"""
Long-Term Memory Module for ReqVibe

This module provides persistent vector storage for requirements using ChromaDB.
Requirements are stored with embeddings for semantic search capabilities.

The LongTermMemory class:
- Stores requirements with their REQ-IDs, text, and metadata
- Provides semantic search functionality to find similar requirements
- Uses sentence-transformers for generating embeddings
- Persists data in a local ChromaDB database
"""

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional
import os

class LongTermMemory:
    """
    Long-term memory storage for requirements using ChromaDB vector database.
    
    This class provides persistent storage and semantic search for requirements.
    Requirements are stored as vectors (embeddings) which allows for semantic
    similarity search - finding requirements that are conceptually similar even
    if they don't share exact keywords.
    
    Architecture:
    - ChromaDB: Vector database for storing embeddings and metadata
    - Sentence Transformers: Generates embeddings from requirement text
    - Collection: Named "requirements" - stores all requirement vectors
    
    Usage:
        ltm = LongTermMemory()
        ltm.save("REQ-001", "User must be able to login", {"priority": "high"})
        results = ltm.search("authentication", top_k=3)
    """
    
    def __init__(self, db_path: str = "db", collection_name: str = "requirements"):
        """
        Initialize the long-term memory system.
        
        Sets up:
        1. ChromaDB client with persistent storage in db/ directory
        2. Sentence transformer model for generating embeddings
        3. Collection for storing requirements (creates if doesn't exist)
        
        Args:
            db_path: Path to the ChromaDB database directory (default: "db")
            collection_name: Name of the ChromaDB collection (default: "requirements")
        
        Side Effects:
            - Creates db/ directory if it doesn't exist
            - Initializes ChromaDB client and collection
            - Loads sentence transformer model into memory
        """
        # Ensure the database directory exists
        os.makedirs(db_path, exist_ok=True)
        
        # Initialize ChromaDB client with persistent storage
        # Settings ensure the database persists to disk
        self.client = chromadb.PersistentClient(
            path=db_path,
            settings=Settings(
                anonymized_telemetry=False,  # Disable telemetry
                allow_reset=True              # Allow collection reset if needed
            )
        )
        
        # Get or create the requirements collection
        # This collection will store all requirement vectors
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "Requirements storage with semantic search"}
        )
        
        # Initialize the sentence transformer model for embeddings
        # all-MiniLM-L6-v2 is a lightweight, fast model good for semantic search
        # It generates 384-dimensional embeddings
        self.embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        
        # Store collection name for reference
        self.collection_name = collection_name
        self.db_path = db_path
    
    def save(self, req_id: str, text: str, metadata: Dict[str, Any] = None) -> bool:
        """
        Save a requirement to long-term memory with vector embedding.
        
        This method:
        1. Generates an embedding vector from the requirement text
        2. Stores the embedding, text, ID, and metadata in ChromaDB
        3. Enables the requirement to be found via semantic search
        
        Args:
            req_id: Unique requirement identifier (e.g., "REQ-001")
            text: Requirement text/description
            metadata: Optional dictionary of additional metadata (e.g., priority, status)
        
        Returns:
            bool: True if save was successful, False otherwise
        
        Example:
            ltm.save(
                "REQ-001",
                "User must be able to login with email and password",
                {"priority": "high", "status": "approved"}
            )
        """
        if metadata is None:
            metadata = {}
        
        try:
            # Generate embedding vector from requirement text
            # The model converts text into a 384-dimensional vector
            embedding = self.embedding_model.encode(text).tolist()
            
            # Flatten metadata for ChromaDB (ChromaDB doesn't support nested dictionaries)
            # Convert nested dicts to flat key-value pairs
            flat_metadata = {}
            
            # Add req_id to metadata for easier retrieval
            flat_metadata["req_id"] = req_id
            
            # Flatten all metadata fields
            for key, value in metadata.items():
                if isinstance(value, dict):
                    # If value is a dict (like volere), flatten it with prefix
                    for sub_key, sub_value in value.items():
                        flat_key = f"{key}_{sub_key}"  # e.g., "volere_goal", "volere_context"
                        # Convert sub_value to string if it's not a primitive type
                        if isinstance(sub_value, (str, int, float, bool)) or sub_value is None:
                            flat_metadata[flat_key] = sub_value
                        else:
                            flat_metadata[flat_key] = str(sub_value)
                elif isinstance(value, (str, int, float, bool)) or value is None:
                    # Primitive types can be stored directly
                    flat_metadata[key] = value
                else:
                    # Convert other types to string
                    flat_metadata[key] = str(value)
            
            # Store in ChromaDB collection
            # - id: Unique identifier (using req_id)
            # - embeddings: The vector representation
            # - documents: The original text (for retrieval)
            # - metadatas: Additional metadata dictionary (must be flat, no nested dicts)
            self.collection.add(
                ids=[req_id],
                embeddings=[embedding],
                documents=[text],
                metadatas=[flat_metadata]
            )
            
            return True
        except Exception as e:
            # Log error in production (for now, just return False)
            print(f"Error saving requirement {req_id}: {str(e)}")
            return False
    
    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Search for similar requirements using semantic similarity.
        
        This method performs semantic search by:
        1. Generating an embedding vector from the query text
        2. Finding the most similar requirement vectors in the database
        3. Returning the top-k most similar requirements with similarity scores
        
        Semantic search finds requirements that are conceptually similar,
        even if they don't share exact keywords. For example, searching for
        "authentication" might find requirements about "login" or "user verification".
        
        Args:
            query: Search query text (e.g., "user login functionality")
            top_k: Number of top results to return (default: 3)
        
        Returns:
            List[Dict[str, Any]]: List of dictionaries, each containing:
                - "id": Requirement ID (e.g., "REQ-001")
                - "text": Requirement text
                - "score": Similarity score (higher = more similar, range typically 0-1)
                - "metadata": Additional metadata dictionary
        
        Example:
            results = ltm.search("authentication system", top_k=5)
            for result in results:
                print(f"{result['id']}: {result['text']} (score: {result['score']:.2f})")
        """
        try:
            # Generate embedding vector from query text
            # Uses the same model as save() to ensure compatibility
            query_embedding = self.embedding_model.encode(query).tolist()
            
            # Perform similarity search in ChromaDB
            # Returns the top_k most similar requirements
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results into a list of dictionaries
            # ChromaDB returns results in a nested structure, we flatten it
            formatted_results = []
            
            if results["ids"] and len(results["ids"][0]) > 0:
                for i in range(len(results["ids"][0])):
                    req_id = results["ids"][0][i]
                    text = results["documents"][0][i]
                    flat_metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                    distance = results["distances"][0][i] if results["distances"] else 0.0
                    
                    # Reconstruct nested metadata structure from flat keys
                    # Convert flat keys like "volere_goal" back to nested dict {"volere": {"goal": ...}}
                    metadata = {}
                    volere_dict = {}
                    
                    for key, value in flat_metadata.items():
                        if key == "req_id":
                            # Skip req_id as it's already in the id field
                            continue
                        elif key.startswith("volere_"):
                            # Extract volere fields
                            volere_key = key.replace("volere_", "")
                            volere_dict[volere_key] = value
                        else:
                            # Other metadata fields
                            metadata[key] = value
                    
                    # Add volere dict if it has any fields
                    if volere_dict:
                        metadata["volere"] = volere_dict
                    
                    # Convert distance to similarity score
                    # ChromaDB uses cosine distance (lower = more similar)
                    # We convert to similarity score (higher = more similar)
                    # Similarity = 1 - distance (for cosine distance)
                    similarity_score = 1.0 - distance
                    
                    formatted_results.append({
                        "id": req_id,
                        "text": text,
                        "score": similarity_score,
                        "metadata": metadata
                    })
            
            return formatted_results
            
        except Exception as e:
            # Log error in production (for now, return empty list)
            print(f"Error searching requirements: {str(e)}")
            return []
    
    def get_all(self) -> List[Dict[str, Any]]:
        """
        Retrieve all stored requirements from the database.
        
        This method is useful for:
        - Listing all requirements
        - Exporting requirements
        - Debugging and inspection
        
        Returns:
            List[Dict[str, Any]]: List of all requirements, each containing:
                - "id": Requirement ID
                - "text": Requirement text
                - "metadata": Additional metadata
        """
        try:
            # Get all items from the collection
            results = self.collection.get(include=["documents", "metadatas"])
            
            formatted_results = []
            if results["ids"]:
                for i in range(len(results["ids"])):
                    flat_metadata = results["metadatas"][i] if results["metadatas"] else {}
                    
                    # Reconstruct nested metadata structure from flat keys
                    metadata = {}
                    volere_dict = {}
                    
                    for key, value in flat_metadata.items():
                        if key == "req_id":
                            # Skip req_id as it's already in the id field
                            continue
                        elif key.startswith("volere_"):
                            # Extract volere fields
                            volere_key = key.replace("volere_", "")
                            volere_dict[volere_key] = value
                        else:
                            # Other metadata fields
                            metadata[key] = value
                    
                    # Add volere dict if it has any fields
                    if volere_dict:
                        metadata["volere"] = volere_dict
                    
                    formatted_results.append({
                        "id": results["ids"][i],
                        "text": results["documents"][i],
                        "metadata": metadata
                    })
            
            return formatted_results
        except Exception as e:
            print(f"Error retrieving all requirements: {str(e)}")
            return []
    
    def delete(self, req_id: str) -> bool:
        """
        Delete a requirement from long-term memory.
        
        Args:
            req_id: Requirement ID to delete
        
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        try:
            self.collection.delete(ids=[req_id])
            return True
        except Exception as e:
            print(f"Error deleting requirement {req_id}: {str(e)}")
            return False
    
    def count(self) -> int:
        """
        Get the total number of requirements stored in the database.
        
        Returns:
            int: Number of requirements in the collection
        """
        try:
            return self.collection.count()
        except Exception as e:
            print(f"Error counting requirements: {str(e)}")
            return 0


# ----------------------------------------------------------------------
# Test Code - Display All Stored Requirements
# ----------------------------------------------------------------------
# Run this file directly to see all requirements stored in the database:
# python long_term_memory.py

if __name__ == "__main__":
    print("=" * 80)
    print("Long-Term Memory - Requirements Database Viewer")
    print("=" * 80)
    print()
    
    try:
        # Initialize long-term memory
        print("Initializing LongTermMemory...")
        ltm = LongTermMemory()
        print("✅ LongTermMemory initialized successfully")
        print()
        
        # Get total count
        total_count = ltm.count()
        print(f"Total requirements stored: {total_count}")
        print()
        
        if total_count == 0:
            print("ℹ️  No requirements found in the database.")
            print("   Requirements will be saved here when auto-save is enabled in the app.")
        else:
            # Get all requirements
            print("Retrieving all requirements...")
            all_requirements = ltm.get_all()
            print(f"✅ Retrieved {len(all_requirements)} requirement(s)")
            print()
            print("=" * 80)
            print("ALL STORED REQUIREMENTS")
            print("=" * 80)
            print()
            
            # Display each requirement
            for idx, req in enumerate(all_requirements, 1):
                req_id = req.get("id", "Unknown")
                req_text = req.get("text", "")
                metadata = req.get("metadata", {})
                
                print(f"[{idx}/{total_count}] {req_id}")
                print("-" * 80)
                print(f"Text: {req_text}")
                
                # Display metadata if available
                if metadata:
                    print("Metadata:")
                    for key, value in metadata.items():
                        if key != "req_id":  # Skip req_id as it's already shown
                            if isinstance(value, dict):
                                print(f"  {key}:")
                                for sub_key, sub_value in value.items():
                                    print(f"    {sub_key}: {sub_value}")
                            else:
                                print(f"  {key}: {value}")
                
                print()
            
            print("=" * 80)
            print(f"Summary: {total_count} requirement(s) found")
            print("=" * 80)
            
            # Optional: Test search functionality
            print()
            print("Testing search functionality...")
            if total_count > 0:
                # Use the first requirement's text as a test query
                test_query = all_requirements[0].get("text", "")[:50]  # First 50 chars
                if test_query:
                    print(f"Search query: '{test_query}...'")
                    search_results = ltm.search(test_query, top_k=3)
                    print(f"Found {len(search_results)} similar requirement(s):")
                    for result in search_results:
                        print(f"  - {result['id']}: {result['text'][:60]}... (score: {result['score']:.3f})")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
