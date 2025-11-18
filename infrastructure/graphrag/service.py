"""
GraphRAG Service for Document Analysis

This service implements a GraphRAG (Graph-based Retrieval Augmented Generation) pipeline
that builds a knowledge graph from structured documents and enables question answering
over the graph using LLM integration.

Features:
- Text chunking for optimal processing
- Entity and relationship extraction
- Knowledge graph construction (using NetworkX)
- Node embeddings generation
- Question answering with graph context
"""

import re
import json
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
import networkx as nx

# Try to import optional dependencies
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False

from monitoring.langsmith import traceable

class GraphRAGIndex:
    """Container for GraphRAG index data."""
    
    def __init__(self):
        self.graph = nx.DiGraph()  # Directed graph for relationships
        self.node_embeddings = {}  # Node ID -> embedding vector
        self.node_texts = {}  # Node ID -> text content
        self.chunks = []  # List of text chunks
        self.metadata = {}  # Additional metadata
        
    def to_dict(self) -> Dict[str, Any]:
        """Serialize index to dictionary (for session state storage)."""
        return {
            'chunks': self.chunks,
            'node_texts': self.node_texts,
            'metadata': self.metadata,
            # Note: graph and embeddings are not serialized to save space
            # They will be rebuilt when needed
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GraphRAGIndex':
        """Deserialize index from dictionary."""
        index = cls()
        index.chunks = data.get('chunks', [])
        index.node_texts = data.get('node_texts', {})
        index.metadata = data.get('metadata', {})
        return index


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """
    Split text into overlapping chunks.
    
    Args:
        text: Input text to chunk
        chunk_size: Target size of each chunk in characters
        overlap: Number of characters to overlap between chunks
        
    Returns:
        List of text chunks
    """
    if not text or len(text) <= chunk_size:
        return [text] if text else []
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        
        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence endings
            last_period = chunk.rfind('.')
            last_newline = chunk.rfind('\n')
            break_point = max(last_period, last_newline)
            
            if break_point > chunk_size * 0.5:  # Only break if we're past halfway
                chunk = chunk[:break_point + 1]
                end = start + break_point + 1
        
        chunks.append(chunk.strip())
        start = end - overlap  # Overlap for context
    
    return chunks


def extract_entities_and_relationships(text: str) -> Tuple[List[str], List[Tuple[str, str, str]]]:
    """
    Extract entities and relationships from text using pattern matching.
    
    This is a simplified extraction. For production, consider using NER models
    or more sophisticated extraction methods.
    
    Args:
        text: Input text
        
    Returns:
        Tuple of (entities, relationships) where:
        - entities: List of entity strings
        - relationships: List of (subject, relation, object) tuples
    """
    entities = []
    relationships = []
    
    # Extract capitalized phrases (potential entities)
    # Pattern: Capitalized words (proper nouns, acronyms)
    entity_pattern = r'\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\b'
    potential_entities = re.findall(entity_pattern, text)
    
    # Filter out common words and keep meaningful entities
    common_words = {'The', 'This', 'That', 'These', 'Those', 'When', 'Where', 
                   'What', 'Which', 'Who', 'How', 'Why', 'Should', 'Must', 
                   'Can', 'Will', 'May', 'Might', 'Could', 'Would'}
    entities = [e for e in potential_entities if e not in common_words and len(e) > 2]
    
    # Extract relationships using common patterns
    # Pattern: "Entity1 verb Entity2" or "Entity1 is/has/contains Entity2"
    relation_patterns = [
        r'([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\s+(?:is|are|has|have|contains|includes|requires|needs|uses|implements)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)',
        r'([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\s+(?:shall|should|must|will|can)\s+([a-z]+(?:\s+[a-z]+)*)',
    ]
    
    for pattern in relation_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            subject = match.group(1)
            obj = match.group(2)
            relation = "related_to"  # Default relation type
            
            # Try to extract the verb as relation
            verb_match = re.search(r'\b(is|are|has|have|contains|includes|requires|needs|uses|implements|shall|should|must|will|can)\b', 
                                 match.group(0), re.IGNORECASE)
            if verb_match:
                relation = verb_match.group(1).lower()
            
            if subject and obj and subject != obj:
                relationships.append((subject, relation, obj))
    
    # Also extract requirement-like patterns
    req_pattern = r'(?:requirement|req|specification|spec)\s+([A-Z0-9]+(?:\.[A-Z0-9]+)*)'
    req_matches = re.findall(req_pattern, text, re.IGNORECASE)
    entities.extend([f"REQ-{req}" for req in req_matches])
    
    return list(set(entities)), relationships


def build_knowledge_graph(chunks: List[str], node_texts: Dict[str, str]) -> nx.DiGraph:
    """
    Build a knowledge graph from text chunks.
    
    Args:
        chunks: List of text chunks
        node_texts: Dictionary mapping node IDs to text content
        
    Returns:
        NetworkX directed graph
    """
    graph = nx.DiGraph()
    
    # Add chunk nodes
    for i, chunk in enumerate(chunks):
        node_id = f"chunk_{i}"
        graph.add_node(node_id, type="chunk", text=chunk)
    
    # Extract entities and relationships from each chunk
    all_entities = set()
    all_relationships = []
    
    for i, chunk in enumerate(chunks):
        entities, relationships = extract_entities_and_relationships(chunk)
        all_entities.update(entities)
        all_relationships.extend(relationships)
        
        # Add entities as nodes
        for entity in entities:
            entity_id = f"entity_{hash(entity) % 10000}"
            if not graph.has_node(entity_id):
                graph.add_node(entity_id, type="entity", name=entity)
            # Link chunk to entity
            graph.add_edge(f"chunk_{i}", entity_id, relation="contains")
        
        # Add relationships as edges
        for subj, rel, obj in relationships:
            subj_id = f"entity_{hash(subj) % 10000}"
            obj_id = f"entity_{hash(obj) % 10000}"
            
            # Ensure nodes exist
            if not graph.has_node(subj_id):
                graph.add_node(subj_id, type="entity", name=subj)
            if not graph.has_node(obj_id):
                graph.add_node(obj_id, type="entity", name=obj)
            
            # Add relationship edge
            graph.add_edge(subj_id, obj_id, relation=rel)
    
    # Add semantic similarity edges between chunks (simplified)
    # In production, use embeddings to find similar chunks
    for i in range(len(chunks)):
        for j in range(i + 1, min(i + 3, len(chunks))):  # Connect nearby chunks
            if not graph.has_edge(f"chunk_{i}", f"chunk_{j}"):
                graph.add_edge(f"chunk_{i}", f"chunk_{j}", relation="follows")
    
    return graph


def generate_embeddings(texts: List[str], model_name: str = "all-MiniLM-L6-v2") -> Dict[str, List[float]]:
    """
    Generate embeddings for texts using sentence transformers.
    
    Args:
        texts: List of texts to embed
        model_name: Name of the sentence transformer model
        
    Returns:
        Dictionary mapping text index to embedding vector
    """
    embeddings = {}
    
    if not HAS_SENTENCE_TRANSFORMERS:
        # Fallback: simple hash-based "embeddings" (not real embeddings)
        for i, text in enumerate(texts):
            # Use a simple hash-based representation
            hash_val = hash(text)
            # Create a pseudo-embedding vector
            pseudo_embedding = [float((hash_val >> j) & 0xFF) / 255.0 for j in range(0, 128, 8)]
            embeddings[str(i)] = pseudo_embedding
        return embeddings
    
    try:
        model = SentenceTransformer(model_name)
        embedding_vectors = model.encode(texts, show_progress_bar=False)
        
        for i, embedding in enumerate(embedding_vectors):
            embeddings[str(i)] = embedding.tolist()
    except Exception as e:
        # Fallback on error
        print(f"Warning: Embedding generation failed: {e}. Using fallback.")
        for i, text in enumerate(texts):
            hash_val = hash(text)
            pseudo_embedding = [float((hash_val >> j) & 0xFF) / 255.0 for j in range(0, 128, 8)]
            embeddings[str(i)] = pseudo_embedding
    
    return embeddings


def process_uploaded_documents(structured_docs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process structured documents from Unstructured API into chunks.
    
    Args:
        structured_docs: Output from process_multiple_documents()
        
    Returns:
        Dictionary with processed document data including chunks
    """
    all_chunks = []
    node_texts = {}
    
    for doc in structured_docs.get('documents', []):
        doc_name = doc.get('filename', 'unknown')
        elements = doc.get('elements', [])
        
        # Extract text from elements
        doc_text_parts = []
        for element in elements:
            if isinstance(element, dict):
                text = element.get('text', '')
                element_type = element.get('type', 'unknown')
                if text:
                    doc_text_parts.append(f"[{element_type}] {text}")
        
        # Combine all text
        full_text = "\n\n".join(doc_text_parts)
        
        # Chunk the text
        chunks = chunk_text(full_text, chunk_size=500, overlap=50)
        
        # Store chunks with metadata
        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc_name}_chunk_{i}"
            all_chunks.append(chunk)
            node_texts[chunk_id] = chunk
    
    return {
        'chunks': all_chunks,
        'node_texts': node_texts,
        'total_chunks': len(all_chunks),
        'documents': structured_docs.get('documents', [])
    }


def build_graphrag_index(structured_docs: Dict[str, Any]) -> GraphRAGIndex:
    """
    Build a complete GraphRAG index from structured documents.
    
    Args:
        structured_docs: Output from process_multiple_documents()
        
    Returns:
        GraphRAGIndex object containing graph, embeddings, and metadata
    """
    index = GraphRAGIndex()
    
    # Process documents into chunks
    processed = process_uploaded_documents(structured_docs)
    index.chunks = processed['chunks']
    index.node_texts = processed['node_texts']
    
    # Build knowledge graph
    index.graph = build_knowledge_graph(index.chunks, index.node_texts)
    
    # Generate embeddings for chunks
    if index.chunks:
        embeddings = generate_embeddings(index.chunks)
        # Map embeddings to chunk indices
        for i, chunk in enumerate(index.chunks):
            chunk_id = f"chunk_{i}"
            if str(i) in embeddings:
                index.node_embeddings[chunk_id] = embeddings[str(i)]
    
    # Store metadata
    index.metadata = {
        'total_chunks': len(index.chunks),
        'total_nodes': index.graph.number_of_nodes(),
        'total_edges': index.graph.number_of_edges(),
        'documents': processed.get('documents', [])
    }
    
    return index


def find_relevant_chunks(query: str, index: GraphRAGIndex, top_k: int = 5) -> List[Tuple[str, float]]:
    """
    Find the most relevant chunks for a query using embeddings.
    
    Args:
        query: User query string
        index: GraphRAGIndex object
        top_k: Number of top chunks to return
        
    Returns:
        List of (chunk_id, similarity_score) tuples
    """
    if not index.chunks or not index.node_embeddings:
        return []
    
    # Generate query embedding
    query_embeddings = generate_embeddings([query])
    if not query_embeddings or '0' not in query_embeddings:
        return []
    
    query_embedding = query_embeddings['0']
    
    # Calculate similarities (cosine similarity)
    similarities = []
    for i, chunk in enumerate(index.chunks):
        chunk_id = f"chunk_{i}"
        if chunk_id in index.node_embeddings:
            chunk_embedding = index.node_embeddings[chunk_id]
            
            # Calculate cosine similarity
            if HAS_NUMPY:
                try:
                    dot_product = np.dot(query_embedding, chunk_embedding)
                    norm_query = np.linalg.norm(query_embedding)
                    norm_chunk = np.linalg.norm(chunk_embedding)
                    similarity = dot_product / (norm_query * norm_chunk + 1e-8)
                except:
                    similarity = 0.0
            else:
                # Fallback: simple dot product (not normalized)
                similarity = sum(a * b for a, b in zip(query_embedding, chunk_embedding)) / 100.0
            
            similarities.append((chunk_id, similarity))
    
    # Sort by similarity and return top_k
    similarities.sort(key=lambda x: x[1], reverse=True)
    return similarities[:top_k]


def extract_graph_context(chunk_ids: List[str], index: GraphRAGIndex, depth: int = 2) -> str:
    """
    Extract context from the knowledge graph around relevant chunks.
    
    Args:
        chunk_ids: List of relevant chunk node IDs
        index: GraphRAGIndex object
        depth: How many hops to traverse in the graph
        
    Returns:
        Context string with relevant graph information
    """
    context_parts = []
    visited_nodes = set()
    
    for chunk_id in chunk_ids:
        if chunk_id not in index.graph:
            continue
        
        # Get chunk text
        chunk_idx = int(chunk_id.split('_')[1]) if '_' in chunk_id else 0
        if chunk_idx < len(index.chunks):
            context_parts.append(f"Relevant Content:\n{index.chunks[chunk_idx]}\n")
        
        # Traverse graph to find related entities and chunks
        try:
            # Get neighbors within depth
            for d in range(depth):
                if d == 0:
                    neighbors = list(index.graph.neighbors(chunk_id))
                else:
                    # Get neighbors of neighbors (simplified BFS)
                    current_level = [chunk_id]
                    for _ in range(d):
                        next_level = []
                        for node in current_level:
                            next_level.extend(list(index.graph.neighbors(node)))
                        current_level = next_level
                    neighbors = current_level
                
                for neighbor in neighbors:
                    if neighbor in visited_nodes:
                        continue
                    visited_nodes.add(neighbor)
                    
                    # Get node attributes
                    if neighbor in index.graph.nodes:
                        node_data = index.graph.nodes[neighbor]
                        node_type = node_data.get('type', 'unknown')
                        if node_type == 'entity':
                            entity_name = node_data.get('name', '')
                            if entity_name:
                                context_parts.append(f"Related Entity: {entity_name}\n")
        except:
            pass  # Ignore graph traversal errors
    
    return "\n".join(context_parts)


@traceable(name="graphrag_answer", run_type="llm")
def answer_question_with_graphrag(
    query: str, 
    index: GraphRAGIndex,
    llm_client,
    model: str = "deepseek-chat"
) -> str:
    """
    Answer a question using GraphRAG index.
    
    Args:
        query: User question
        index: GraphRAGIndex object
        llm_client: LLM client instance
        model: Model name to use
        
    Returns:
        Answer string
    """
    if not index.chunks:
        return "No document context available. Please upload and process documents first."
    
    # Find relevant chunks
    relevant_chunks = find_relevant_chunks(query, index, top_k=5)
    
    if not relevant_chunks:
        return "Could not find relevant information in the documents. Please try rephrasing your question."
    
    # Extract graph context
    chunk_ids = [chunk_id for chunk_id, _ in relevant_chunks]
    graph_context = extract_graph_context(chunk_ids, index, depth=2)
    
    # Build prompt with context
    context_text = "\n\n".join([
        index.chunks[int(cid.split('_')[1])] 
        for cid in chunk_ids 
        if '_' in cid and cid.split('_')[1].isdigit()
    ])
    
    system_prompt = """You are a helpful assistant that answers questions based on the provided document context.
Use the document context to answer the user's question accurately. If the context doesn't contain enough
information to answer the question, say so clearly."""
    
    user_prompt = f"""Based on the following document context, please answer the user's question.

Document Context:
{context_text}

{graph_context}

User Question: {query}

Please provide a clear and accurate answer based on the document context."""
    
    try:
        # Call LLM
        response = llm_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        answer = response.choices[0].message.content
        return answer
        
    except Exception as e:
        return f"Error generating answer: {str(e)}"


def is_document_related_query(query: str) -> bool:
    """
    Determine if a query is likely related to uploaded documents.
    
    Args:
        query: User query string
        
    Returns:
        True if query seems document-related
    """
    query_lower = query.lower()
    
    # Keywords that suggest document-related queries
    doc_keywords = [
        'document', 'requirement', 'specification', 'spec', 'req',
        'what does', 'what is', 'explain', 'describe', 'tell me about',
        'according to', 'in the document', 'from the document',
        'what are', 'list', 'show me', 'find', 'where is'
    ]
    
    return any(keyword in query_lower for keyword in doc_keywords)

