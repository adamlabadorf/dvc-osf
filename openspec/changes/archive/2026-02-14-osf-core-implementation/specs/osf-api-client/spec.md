# OSF API Client Specification

## ADDED Requirements

### Requirement: API client initialization
The system SHALL provide an OSFAPIClient class that can be initialized with a base URL and authentication token.

#### Scenario: Initialize with default API URL
- **WHEN** OSFAPIClient is instantiated without a base_url parameter
- **THEN** the client SHALL use 'https://api.osf.io/v2' as the default base URL

#### Scenario: Initialize with custom API URL
- **WHEN** OSFAPIClient is instantiated with a custom base_url parameter
- **THEN** the client SHALL use the provided base URL for all API requests

#### Scenario: Initialize with authentication token
- **WHEN** OSFAPIClient is instantiated with a token parameter
- **THEN** the client SHALL include 'Authorization: Bearer <token>' header in all requests

### Requirement: HTTP GET requests
The system SHALL support HTTP GET requests to OSF API endpoints with proper authentication and error handling.

#### Scenario: Successful GET request
- **WHEN** client makes a GET request to a valid endpoint
- **THEN** the system SHALL return the JSON response body as a dictionary

#### Scenario: GET request with authentication
- **WHEN** client makes a GET request with a token configured
- **THEN** the system SHALL include the 'Authorization: Bearer <token>' header in the request

#### Scenario: GET request with query parameters
- **WHEN** client makes a GET request with query parameters
- **THEN** the system SHALL properly encode and append query parameters to the URL

### Requirement: HTTP POST requests
The system SHALL support HTTP POST requests to OSF API endpoints for creating resources.

#### Scenario: POST request with JSON body
- **WHEN** client makes a POST request with a JSON payload
- **THEN** the system SHALL set 'Content-Type: application/json' header and serialize the payload

#### Scenario: POST request returns created resource
- **WHEN** client makes a successful POST request
- **THEN** the system SHALL return the created resource data from the response

### Requirement: HTTP PUT requests
The system SHALL support HTTP PUT requests to OSF API endpoints for updating resources.

#### Scenario: PUT request for file upload
- **WHEN** client makes a PUT request with file data
- **THEN** the system SHALL stream the file content in the request body

#### Scenario: PUT request with metadata
- **WHEN** client makes a PUT request with metadata updates
- **THEN** the system SHALL serialize the metadata as JSON in the request body

### Requirement: HTTP DELETE requests
The system SHALL support HTTP DELETE requests to OSF API endpoints for deleting resources.

#### Scenario: Successful DELETE request
- **WHEN** client makes a DELETE request to a valid resource
- **THEN** the system SHALL return success (no exception raised)

#### Scenario: DELETE non-existent resource
- **WHEN** client makes a DELETE request to a non-existent resource
- **THEN** the system SHALL raise OSFNotFoundError

### Requirement: Connection pooling
The system SHALL use a connection pool to reuse HTTP connections for multiple requests.

#### Scenario: Reuse connections for multiple requests
- **WHEN** client makes multiple requests to the same host
- **THEN** the system SHALL reuse the same TCP connection

#### Scenario: Configure pool size
- **WHEN** OSFAPIClient is initialized
- **THEN** the system SHALL create a connection pool with configurable maximum size (default: 10)

### Requirement: Request timeout handling
The system SHALL enforce timeouts on all HTTP requests to prevent indefinite blocking.

#### Scenario: Default timeout
- **WHEN** client makes a request without specifying a timeout
- **THEN** the system SHALL use a default timeout of 30 seconds

#### Scenario: Custom timeout
- **WHEN** client makes a request with a custom timeout parameter
- **THEN** the system SHALL use the specified timeout value

#### Scenario: Timeout exceeded
- **WHEN** a request exceeds the configured timeout
- **THEN** the system SHALL raise OSFConnectionError with a timeout message

### Requirement: Response status code handling
The system SHALL handle HTTP response status codes appropriately and raise specific exceptions.

#### Scenario: 200 OK response
- **WHEN** API returns 200 status code
- **THEN** the system SHALL return the response data without raising an exception

#### Scenario: 201 Created response
- **WHEN** API returns 201 status code
- **THEN** the system SHALL return the created resource data without raising an exception

#### Scenario: 204 No Content response
- **WHEN** API returns 204 status code
- **THEN** the system SHALL return None without raising an exception

#### Scenario: 400 Bad Request response
- **WHEN** API returns 400 status code
- **THEN** the system SHALL raise OSFAPIError with the error message from response

#### Scenario: 401 Unauthorized response
- **WHEN** API returns 401 status code
- **THEN** the system SHALL raise OSFAuthenticationError

#### Scenario: 403 Forbidden response
- **WHEN** API returns 403 status code
- **THEN** the system SHALL raise OSFPermissionError

#### Scenario: 404 Not Found response
- **WHEN** API returns 404 status code
- **THEN** the system SHALL raise OSFNotFoundError

#### Scenario: 429 Rate Limit response
- **WHEN** API returns 429 status code
- **THEN** the system SHALL raise OSFRateLimitError

#### Scenario: 500 Internal Server Error response
- **WHEN** API returns 500 status code
- **THEN** the system SHALL raise OSFAPIError and mark as retryable

#### Scenario: 502 Bad Gateway response
- **WHEN** API returns 502 status code
- **THEN** the system SHALL raise OSFConnectionError and mark as retryable

#### Scenario: 503 Service Unavailable response
- **WHEN** API returns 503 status code
- **THEN** the system SHALL raise OSFConnectionError and mark as retryable

### Requirement: Automatic retry for transient failures
The system SHALL automatically retry requests that fail due to transient errors.

#### Scenario: Retry on connection error
- **WHEN** a request fails with a connection error
- **THEN** the system SHALL retry up to the configured maximum (default: 3 times)

#### Scenario: Retry with exponential backoff
- **WHEN** a request is retried
- **THEN** the system SHALL wait progressively longer between retries (exponential backoff factor: 2.0)

#### Scenario: Retry on 500 error
- **WHEN** API returns 500 status code
- **THEN** the system SHALL retry the request up to the maximum retry count

#### Scenario: Retry on 502 error
- **WHEN** API returns 502 status code
- **THEN** the system SHALL retry the request up to the maximum retry count

#### Scenario: Retry on 503 error
- **WHEN** API returns 503 status code
- **THEN** the system SHALL retry the request up to the maximum retry count

#### Scenario: No retry on client errors
- **WHEN** API returns 4xx status code (except 429)
- **THEN** the system SHALL NOT retry and SHALL raise an exception immediately

#### Scenario: Retry exhausted
- **WHEN** all retry attempts are exhausted
- **THEN** the system SHALL raise the last encountered exception

### Requirement: Rate limit handling
The system SHALL handle OSF API rate limits with appropriate backoff strategy.

#### Scenario: Rate limit with Retry-After header
- **WHEN** API returns 429 with 'Retry-After' header
- **THEN** the system SHALL wait for the specified duration before retrying

#### Scenario: Rate limit without Retry-After header
- **WHEN** API returns 429 without 'Retry-After' header
- **THEN** the system SHALL use exponential backoff with longer delays than normal retries

#### Scenario: Rate limit retry count
- **WHEN** rate limit is encountered
- **THEN** the system SHALL retry up to the configured maximum retry count

### Requirement: Streaming downloads
The system SHALL support streaming large file downloads without loading entire files into memory.

#### Scenario: Stream file content
- **WHEN** client requests a file download with streaming enabled
- **THEN** the system SHALL return a response object that yields chunks of data

#### Scenario: Configure chunk size
- **WHEN** client requests a streaming download
- **THEN** the system SHALL use a configurable chunk size (default: 8192 bytes)

#### Scenario: Stream large files
- **WHEN** client downloads a file larger than available memory
- **THEN** the system SHALL stream the file without loading it entirely into memory

### Requirement: Request headers customization
The system SHALL allow custom headers to be included in requests.

#### Scenario: Add custom headers
- **WHEN** client makes a request with custom headers parameter
- **THEN** the system SHALL include the custom headers in the HTTP request

#### Scenario: Preserve authentication header
- **WHEN** custom headers are provided
- **THEN** the system SHALL still include the authentication header if token is configured

### Requirement: API response pagination
The system SHALL handle paginated API responses and provide access to all pages of results.

#### Scenario: Detect paginated response
- **WHEN** API returns a response with 'links.next' field
- **THEN** the system SHALL identify the response as paginated

#### Scenario: Fetch next page
- **WHEN** client requests the next page of a paginated response
- **THEN** the system SHALL make a request to the URL in 'links.next' field

#### Scenario: Iterate through all pages
- **WHEN** client requests all results from a paginated endpoint
- **THEN** the system SHALL automatically fetch all pages until 'links.next' is null

### Requirement: Error message extraction
The system SHALL extract detailed error messages from OSF API error responses.

#### Scenario: Parse error from response body
- **WHEN** API returns an error response with JSON body
- **THEN** the system SHALL extract the error message from the response and include it in the exception

#### Scenario: Handle malformed error response
- **WHEN** API returns an error response with invalid or missing error message
- **THEN** the system SHALL include the HTTP status code and a generic error message in the exception

### Requirement: Session management
The system SHALL manage HTTP sessions efficiently for the lifetime of the client.

#### Scenario: Create session on initialization
- **WHEN** OSFAPIClient is instantiated
- **THEN** the system SHALL create a requests.Session object

#### Scenario: Reuse session for all requests
- **WHEN** client makes multiple requests
- **THEN** the system SHALL use the same session object for all requests

#### Scenario: Close session on cleanup
- **WHEN** OSFAPIClient is destroyed or explicitly closed
- **THEN** the system SHALL close the underlying HTTP session
