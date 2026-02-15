"""Mock OSF API response fixtures for testing."""

# Mock file metadata response
FILE_METADATA = {
    "data": {
        "id": "file123",
        "type": "files",
        "attributes": {
            "kind": "file",
            "name": "test_file.csv",
            "size": 1024,
            "date_created": "2024-01-01T00:00:00",
            "date_modified": "2024-01-02T00:00:00",
            "extra": {
                "hashes": {
                    "md5": "5d41402abc4b2a76b9719d911017c592",
                    "sha256": "abc123def456",
                }
            },
        },
        "links": {
            "info": "https://api.osf.io/v2/files/file123/",
            "download": "https://files.osf.io/v1/file123/download",
        },
    }
}

# Mock directory listing response
DIRECTORY_LISTING = {
    "data": [
        {
            "id": "file1",
            "type": "files",
            "attributes": {
                "kind": "file",
                "name": "file1.csv",
                "size": 512,
                "date_modified": "2024-01-01T00:00:00",
                "extra": {"hashes": {"md5": "abc123"}},
            },
        },
        {
            "id": "file2",
            "type": "files",
            "attributes": {
                "kind": "file",
                "name": "file2.csv",
                "size": 1024,
                "date_modified": "2024-01-02T00:00:00",
                "extra": {"hashes": {"md5": "def456"}},
            },
        },
        {
            "id": "folder1",
            "type": "files",
            "attributes": {
                "kind": "folder",
                "name": "subdir",
                "size": None,
                "date_modified": "2024-01-01T00:00:00",
                "extra": {"hashes": {}},
            },
        },
    ],
    "links": {},
}

# Mock paginated response (page 1)
PAGINATED_RESPONSE_PAGE1 = {
    "data": [
        {
            "id": "file1",
            "attributes": {
                "name": "file1.csv",
                "kind": "file",
            },
        },
        {
            "id": "file2",
            "attributes": {
                "name": "file2.csv",
                "kind": "file",
            },
        },
    ],
    "links": {"next": "https://api.osf.io/v2/nodes/abc123/files/osfstorage/?page=2"},
}

# Mock paginated response (page 2)
PAGINATED_RESPONSE_PAGE2 = {
    "data": [
        {
            "id": "file3",
            "attributes": {
                "name": "file3.csv",
                "kind": "file",
            },
        },
    ],
    "links": {},
}

# Mock error responses
ERROR_401 = {
    "errors": [
        {
            "detail": "Authentication credentials were not provided.",
            "status": "401",
        }
    ]
}

ERROR_403 = {
    "errors": [
        {
            "detail": "You do not have permission to perform this action.",
            "status": "403",
        }
    ]
}

ERROR_404 = {
    "errors": [
        {
            "detail": "Not found.",
            "status": "404",
        }
    ]
}

ERROR_429 = {
    "errors": [
        {
            "detail": "Request was throttled.",
            "status": "429",
        }
    ]
}

ERROR_500 = {
    "errors": [
        {
            "detail": "Internal server error.",
            "status": "500",
        }
    ]
}
