# Style Preference API Documentation

## Base URL
`https://haider.techrealm.online/api`

## Authentication
All endpoints except health check require an AI-ID header obtained from the preference creation endpoint.

Default Test AI-ID: `AI_test_user_123_2d550589`

## Endpoints

### Health Check
Verify API availability.

```http
GET /api
```

**Response** `200 OK`
```json
{
    "status": "ok"
}
```

### Create Preference
Initialize a new style preference session.

```http
POST /api/preference
```

**Request Body**
```json
{
    "access_id": "test_user_123",
    "gender": "men|women"
}
```

**Response** `200 OK`
```json
{
    "preference_id": "550e8400-e29b-41d4-a716-446655440000",
    "ai_id": "AI_test_user_123_2d550589"
}
```

### Process Iteration
Submit feedback and receive next image.

```http
POST /api/preference/{preference_id}/iteration/{iteration_id}
```

**Headers**
```
AI-ID: AI_test_user_123_2d550589
```

**Path Parameters**
- `preference_id`: UUID from preference creation
- `iteration_id`: Number 1-30

**Request Body (Iterations 1-29)**
```json
{
    "feedback": "like|dislike"
}
```

**Request Body (Iteration 30)**
```json
{
    "feedback": "like|dislike",
    "style": "casual",
    "image_key": "women/casual/img123.jpg"
}
```

**Response (Iterations 1-29)** `200 OK`
```json
{
    "image_url": "https://example.com/image.jpg",
    "iteration": 1,
    "completed": false,
    "style": "casual",
    "image_key": "women/casual/img123.jpg"
}
```

**Response (Iteration 30)** `200 OK`
```json
{
    "image_url": null,
    "iteration": 30,
    "completed": true
}
```

### Save Profile
Save completed preference profile.

```http
POST /api/preference/{preference_id}/profile
```

**Headers**
```
AI-ID: AI_test_user_123_2d550589
```

**Response** `200 OK`
```json
{
    "message": "Profile saved successfully"
}
```

### Get Profile
Retrieve saved preference profile.

```http
GET /api/preference/{preference_id}/profile
```

**Headers**
```
AI-ID: AI_test_user_123_2d550589
```

**Response** `200 OK`
```json
{
    "top_styles": {
        "casual": 0.8,
        "formal": 0.6,
        "sporty": 0.4
    },
    "selection_history": [
        {
            "image": "women/casual/img123.jpg",
            "style": "casual",
            "feedback": "Like",
            "score_change": 0.1,
            "current_score": 0.8,
            "timestamp": 1679444374
        }
    ]
}
```

## Error Responses

**400 Bad Request**
```json
{
    "error": "Invalid parameters"
}
```

**401 Unauthorized**
```json
{
    "error": "Invalid AI ID"
}
```

**404 Not Found**
```json
{
    "error": "Resource not found"
}
```

## Usage Flow
1. Create preference session
2. Process 30 iterations:
   - Iterations 1-29: Send feedback, receive next image
   - Iteration 30: Send final feedback with style/image data
3. Save profile
4. Retrieve profile data as needed

## Testing
Use the provided test AI-ID for development:
```
AI_test_user_123_2d550589
```
