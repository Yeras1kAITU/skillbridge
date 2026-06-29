import os
import cloudinary
import cloudinary.uploader
from cloudinary.exceptions import Error as CloudinaryError

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True  # Use HTTPS
)

def upload_file(file_content, public_id: str = None, folder: str = "skillbridge"):
    """
    Upload a file to Cloudinary

    Args:
        file_content: File content (bytes or file object)
        public_id: Unique identifier for the file (optional)
        folder: Folder name in Cloudinary

    Returns:
        dict: Upload result with URL, public_id, etc.
    """
    try:
        # If no public_id provided, generate one
        if not public_id:
            import uuid
            public_id = f"{folder}/{uuid.uuid4().hex}"
        else:
            public_id = f"{folder}/{public_id}"

        result = cloudinary.uploader.upload(
            file_content,
            public_id=public_id,
            resource_type="auto",  # Auto-detect file type
            folder=folder,
            use_filename=True,
            unique_filename=True,
            overwrite=True
        )

        return {
            "url": result.get("secure_url"),
            "public_id": result.get("public_id"),
            "resource_type": result.get("resource_type"),
            "format": result.get("format"),
            "bytes": result.get("bytes"),
            "created_at": result.get("created_at")
        }
    except CloudinaryError as e:
        print(f"Cloudinary upload error: {e}")
        return None

def delete_file(public_id: str) -> bool:
    """
    Delete a file from Cloudinary

    Args:
        public_id: The public_id of the file to delete

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        result = cloudinary.uploader.destroy(public_id)
        return result.get("result") == "ok"
    except CloudinaryError as e:
        print(f"Cloudinary delete error: {e}")
        return False

def get_file_url(public_id: str, options: dict = None) -> str:
    """
    Get the URL of a file in Cloudinary

    Args:
        public_id: The public_id of the file
        options: Additional Cloudinary options (e.g., width, height, crop)

    Returns:
        str: The file URL
    """
    if options is None:
        options = {}

    # Default options for optimization
    default_options = {
        "fetch_format": "auto",
        "quality": "auto"
    }
    default_options.update(options)

    return cloudinary.CloudinaryImage(public_id).build_url(**default_options)

def upload_portfolio_file(file_content, user_id: str, title: str, category: str = "other") -> dict:
    """
    Upload a portfolio file to Cloudinary

    Args:
        file_content: File content
        user_id: User ID
        title: File title
        category: File category

    Returns:
        dict: Upload result with URL and public_id
    """
    # Create a clean public_id
    import re
    clean_title = re.sub(r'[^a-zA-Z0-9_-]', '_', title)[:50]
    public_id = f"users/{user_id}/portfolio/{clean_title}_{int(time.time())}"

    return upload_file(file_content, public_id)

def delete_portfolio_file(public_id: str) -> bool:
    """
    Delete a portfolio file from Cloudinary

    Args:
        public_id: The public_id of the file

    Returns:
        bool: True if successful, False otherwise
    """
    return delete_file(public_id)