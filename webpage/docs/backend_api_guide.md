# Odysseia Forum Backend API Guide

This document serves as a comprehensive guide for frontend developers integrating with the Odysseia Forum backend API.

**Base URL**: `/v1` (e.g., `http://localhost:10810/v1` in local dev)

## Authentication (`/auth`)

The backend uses Discord OAuth2 for authentication.

### Login
- **Endpoint**: `GET /auth/login`
- **Description**: Redirects the user to the Discord OAuth2 authorization page.
- **Flow**:
    1. Frontend redirects user to `/auth/login`.
    2. Backend redirects to Discord.
    3. User approves app.
    4. Discord redirects back to backend `/auth/callback`.
    5. Backend redirects to frontend (configured via `FRONTEND_URL`) with a URL hash containing the token: `/#token=<JWT_TOKEN>`.
    6. Frontend extracts token from hash and stores it (e.g., `localStorage`).

### Logout
- **Endpoint**: `GET /auth/logout`
- **Description**: Clears the session and redirects the user.
- **Note**: Frontend should also clear the token from storage.

### Check Auth
- **Endpoint**: `GET /auth/checkauth`
- **Description**: Verifies the current session and returns user info.
- **Headers**: `Authorization: Bearer <TOKEN>`
- **Response**:
  ```json
  {
    "loggedIn": true,
    "user": {
      "id": "string",
      "username": "string",
      "global_name": "string",
      "avatar": "string",
      "discriminator": "string"
    },
    "unread_count": 0
  }
  ```

---

## Search & Tags (`/search`, `/meta`)

### Global Search
- **Endpoint**: `POST /search/`
- **Description**: Search for threads based on keywords, tags, and channel filters.
- **Request Body**:
  ```json
  {
    "keywords": "string (optional)",
    "channel_ids": ["string (optional)"],
    "include_tags": ["string (optional)"],
    "exclude_tags": ["string (optional)"],
    "limit": 20,
    "offset": 0
  }
  ```
- **Response**: `SearchResponse` object containing list of threads and total count.

### Get Channels & Tags
- **Endpoint**: `GET /meta/channels`
- **Description**: Retrieves all indexed channels and their available tags.
- **Response**:
  ```json
  [
    {
      "id": "string",
      "name": "string",
      "category_name": "string",
      "tags": [
        { "id": "string", "name": "string" }
      ]
    }
  ]
  ```
- **Note**: There is **NO** standalone `/tags` endpoint. Tags are bound to channels.

---

## Follows (`/follows`)

Manage user's followed threads.

### Get Followed Threads
- **Endpoint**: `GET /follows/`
- **Description**: Returns a list of threads the user is following.

### Follow a Thread
- **Endpoint**: `POST /follows/{thread_id}`
- **Description**: Follows a specific thread.

### Unfollow a Thread
- **Endpoint**: `DELETE /follows/{thread_id}`
- **Description**: Unfollows a specific thread.

### Get Unread Count
- **Endpoint**: `GET /follows/unread-count`
- **Description**: Returns the number of unread followed threads.

### Mark All Viewed
- **Endpoint**: `POST /follows/mark-viewed`
- **Description**: Marks all followed threads as viewed.

---

## Banner Application (`/banner`)

Manage thread banner applications.

### Apply for Banner
- **Endpoint**: `POST /banner/apply`
- **Description**: Submit a banner application for a thread.
- **Permissions**: User must be the author of the thread.
- **Request Body**:
  ```json
  {
    "thread_id": "string (digits only)",
    "cover_image_url": "string (valid URL)",
    "target_scope": "string ('global' or channel_id)"
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "message": "string",
    "application_id": 123
  }
  ```

### Get Active Banners
- **Endpoint**: `GET /banner/active`
- **Query Params**: `channel_id` (optional)
- **Description**: Returns currently active banners.

---

## Image Refresh (`/fetch-images`)

Refresh thread thumbnails from Discord.

### Batch Refresh
- **Endpoint**: `POST /fetch-images/`
- **Description**: Manually triggers a refresh of thread thumbnails by fetching the latest images from the Discord thread's first message.
- **Request Body**:
  ```json
  {
    "items": [
      {
        "thread_id": 123456789,
        "channel_id": 123 (optional)
      }
    ]
  }
  ```
- **Response**:
  ```json
  {
    "results": [
      {
        "thread_id": "string",
        "thumbnail_urls": ["string"],
        "updated": true,
        "error": null
      }
    ]
  }
  ```

---

## User Preferences (`/preferences`)

Manage user-specific settings.

### Get Preferences
- **Endpoint**: `GET /preferences/users/{user_id}`
- **Description**: Get search preferences for a user.

### Update Preferences
- **Endpoint**: `PUT /preferences/users/{user_id}`
- **Description**: Update search preferences.
- **Request Body**: `UserPreferencesUpdateRequest` (schema varies based on backend implementation).
