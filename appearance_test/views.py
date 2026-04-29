import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from appearance_test.constants import BODY_SHAPES, COLOR_PALETTES
from appearance_test.recommendations_lookup import build_api_payload, lookup_row

def analyze_color_type(client):
    """Determines season (Winter, Summer, Autumn, Spring)"""
    undertone = client.get('undertone', 'neutral')
    hair = client.get('hair_color', '').lower()
    eyes = client.get('eyes_color', '').lower()

    # Temperature (Undertone)
    is_warm = undertone in ['warm', 'olive', 'yellow']

    # If neutral, check tanning and hair warmth
    if undertone == 'neutral':
        if client.get('tanning_reaction') == 'tans easily' or 'gold' in hair:
            is_warm = True
        else:
            is_warm = False  # Considered Cool

    # Hair brightness
    is_light_hair = any(c in hair for c in ['blonde', 'light', 'red', 'ginger'])

    # Determine Season
    if is_warm:
        return "Spring" if is_light_hair else "Autumn"
    else:
        if is_light_hair and ('ash' in hair or 'light' in eyes):
            return "Summer"
        return "Winter"

def analyze_body_shape(client):
    """Determines body shape based on measurements"""
    bust = client.get('bust', 0)
    waist = client.get('waist', 0)
    hips = client.get('hips', 0)

    if bust == 0 or hips == 0:
        return "Unknown"

    waist_hip_ratio = waist / hips
    bust_hip_ratio = bust / hips

    if bust_hip_ratio >= 1.05:
        return "Inverted Triangle"
    elif bust_hip_ratio <= 0.95:
        return "Pear"
    elif waist_hip_ratio < 0.75:
        return "Hourglass"
    elif waist_hip_ratio > 0.85:
        return "Apple"
    else:
        return "Rectangle"

def client_analysis_view(request):
    # Mock Input Data simulating DB retrieval
    client_data = {
        "id": 1,
        "name": "Ольга Мельник",
        "user_name": "olha.m",
        "email": "olha@example.com",
        "phone_number": "+380931234567",
        "location": "Київ",
        "age": 27,
        "height_sm": 168,
        "eyes_color": "green",
        "skin_color": "light",
        "hair_color": "dark brown",
        "image_url": "https://example.com/clients/olha.jpg",
        "face_shape": "oval",
        "forehead_height": "medium",
        "eye_shape": "almond",
        "eye_size": "medium",
        "nose_shape": "straight",
        "lips_fullness": "medium",
        "chin_shape": "rounded",
        "brow_thickness": "medium",
        "brow_arch": "soft",
        "undertone": "neutral",
        "freckles": False,
        "tanning_reaction": "tans easily",
        "shoulders_width": "average",
        "bust": 88,
        "waist": 66,
        "hips": 94,
        "leg_length_ratio": "balanced"
    }

    # 1. Run Analysis
    color_season = analyze_color_type(client_data)
    body_shape = analyze_body_shape(client_data)

    # 2. Get recommendations from Knowledge Base
    color_info = COLOR_PALETTES.get(color_season, {})
    body_info = BODY_SHAPES.get(body_shape, {})

    # 3. Form Response
    result = {
        "client": {
            "id": client_data['id'],
            "name": client_data['name'],
            "user_name": client_data['user_name'],
            "email": client_data['email'],
            "phone_number": client_data['phone_number'],
            "location": client_data['location'],
            "age": client_data['age'],
            "height_sm": client_data['height_sm'],
            "image_url": client_data['image_url'],
            "face_shape": client_data['face_shape'],
            "forehead_height": client_data['forehead_height'],
            "eye_shape": client_data['eye_shape'],
            "eye_size": client_data['eye_size'],
            "nose_shape": client_data['nose_shape'],
            "lips_fullness": client_data['lips_fullness'],
            "chin_shape": client_data['chin_shape'],
            "brow_thickness": client_data['brow_thickness'],
            "brow_arch": client_data['brow_arch'],
            "skin_color": client_data['skin_color'],
            "hair_color": client_data['hair_color'],
            "eyes_color": client_data['eyes_color'],
            "undertone": client_data['undertone'],
            "freckles": client_data['freckles'],
            "tanning_reaction": client_data['tanning_reaction'],
            "shoulders_width": client_data['shoulders_width'],
            "bust": client_data['bust'],
            "waist": client_data['waist'],
            "hips": client_data['hips'],
            "leg_length_ratio": client_data['leg_length_ratio']
        },
        "analysis_result": {
            "color_type": {
                "season": color_season,
                "description": color_info.get("description"),
                "palette": color_info.get("palette_hex"),
                "advice": {
                    "best_colors": color_info.get("best_colors"),
                    "least_colors": color_info.get("least_colors")
                }
            },
            "body_type": {
                "shape": body_shape,
                "description": body_info.get("description"),
                "advice": {
                    "best_clothes": body_info.get("best_clothes"),
                    "avoid_clothes": body_info.get("avoid_clothes")
                }
            }
        },
        "look_alike_style": f"Style based on {color_season} colors and {body_shape} lines."
    }

    return JsonResponse(result, safe=False)


@csrf_exempt
def analyse_appearance_view(request):
    """
    POST /api/appearance_test/analyse/
    Values must match recommendations.csv labels exactly.

    Body (JSON):
      hair_color       — e.g. "Black", "Blonde"
      eyes_color       — e.g. "Brown", "Light Blue"
      skin_tone        — e.g. "Very Fair", "Medium"
      undertone        — "Warm" | "Cool" | "Neutral"
      torso_length     — "Short Torso" | "Long Torso" | "Balanced"
      body_proportion  — e.g. "Hourglass", "Inverted Triangle"
    """
    if request.method != 'POST':
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    required = (
        'hair_color',
        'eyes_color',
        'skin_tone',
        'undertone',
        'torso_length',
        'body_proportion',
    )
    missing = [k for k in required if not str(data.get(k, '')).strip()]
    if missing:
        return JsonResponse({'error': 'Missing fields', 'missing': missing}, status=400)

    inputs = {k: str(data[k]).strip() for k in required}

    row = lookup_row(
        inputs['hair_color'],
        inputs['eyes_color'],
        inputs['skin_tone'],
        inputs['undertone'],
        inputs['torso_length'],
        inputs['body_proportion'],
    )
    if row is None:
        return JsonResponse(
            {'error': 'No matching recommendation row for this combination.'},
            status=404,
        )

    payload = build_api_payload(row, inputs)
    return JsonResponse(payload, safe=False)
