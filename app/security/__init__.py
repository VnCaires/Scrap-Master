"""Safety policy package."""

from app.security.masking import mask_email, mask_name

__all__ = ["mask_email", "mask_name"]
