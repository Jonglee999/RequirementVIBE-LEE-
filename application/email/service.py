"""
Email Verification Service for ReqVibe

Email functionality is temporarily disabled. The implementation is kept as a stub so it can be re-enabled later.
"""

# NOTE: Email features are currently disabled. To enable again:
#   - Restore the imports (os, resend, etc.)
#   - Restore class logic to send verification codes
#   - Configure Resend API credentials

# The following stub keeps the same API so other modules can call it without modification.

from typing import Optional, Tuple


class EmailVerificationService:
    """Stubbed email service with all functionality disabled."""

    def validate_email(self, email: str) -> Tuple[bool, str]:
        if not email or not email.strip():
            return False, "Email address is required"
        email = email.strip()
        if "@" not in email:
            return False, "Invalid email format"
        return True, ""

    def generate_verification_code(self, length: int = 6) -> str:
        return "000000"

    def send_verification_code(self, email: str, purpose: str = "registration") -> Tuple[bool, str]:
        # Email sending disabled; return informational message.
        return True, (
            "Verification email is temporarily disabled. Please contact support if you need assistance."
        )

    def verify_code(self, email: str, code: str, purpose: str = "registration") -> Tuple[bool, str]:
        # Always succeed since code sending is disabled.
        return True, "Verification skipped (email service disabled)."

    def clear_expired_codes(self):
        pass


def get_email_service() -> EmailVerificationService:
    return EmailVerificationService()

