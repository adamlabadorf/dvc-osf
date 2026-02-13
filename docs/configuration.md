# Configuration Guide

## OSF Authentication

### Creating a Personal Access Token

1. Log in to [OSF](https://osf.io)
2. Navigate to Settings → Personal Access Tokens
3. Click "Create token"
4. Select appropriate scopes (typically `osf.full_read` and `osf.full_write`)
5. Save the token securely

### Configuring the Token

#### Option 1: DVC Remote Configuration

```bash
dvc remote modify myremote token YOUR_TOKEN
```

#### Option 2: Environment Variable

```bash
export OSF_TOKEN=YOUR_TOKEN
```

#### Option 3: Configuration File

Store token in DVC config:

```bash
dvc remote modify --local myremote token YOUR_TOKEN
```

## Remote Configuration

### Basic Remote Setup

```bash
# Add OSF remote
dvc remote add myremote osf://PROJECT_ID/STORAGE_NAME

# Configure authentication
dvc remote modify myremote token YOUR_TOKEN
```

### Configuration Options

Available configuration options:

- `token`: OSF personal access token (required)
- `project_id`: OSF project identifier
- `timeout`: Request timeout in seconds (default: 30)
- `retries`: Number of retry attempts (default: 3)

Example with all options:

```bash
dvc remote modify myremote token YOUR_TOKEN
dvc remote modify myremote timeout 60
dvc remote modify myremote retries 5
```

## Project Structure

### OSF URL Format

```
osf://PROJECT_ID/STORAGE_NAME/path/to/data
```

Where:
- `PROJECT_ID`: Your OSF project ID (from project URL)
- `STORAGE_NAME`: Storage provider (typically `osfstorage`)
- `path/to/data`: Path within the storage

## Security Considerations

- **Never commit tokens to git**: Use `--local` flag or environment variables
- **Use token scopes**: Limit token permissions to what's needed
- **Rotate tokens regularly**: Create new tokens periodically
- **Use project-specific tokens**: Consider separate tokens for different projects

## Troubleshooting

### Authentication Errors

If you encounter authentication errors:

1. Verify token is valid in OSF settings
2. Check token has correct scopes
3. Ensure token is configured correctly in DVC

### Connection Issues

If you experience connection problems:

1. Check network connectivity
2. Verify OSF service status
3. Increase timeout value
4. Check firewall settings

## Next Steps

- See [Development Guide](development.md) for development setup
- See [README](../README.md) for usage examples
