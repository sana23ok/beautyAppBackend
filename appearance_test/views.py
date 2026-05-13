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


def _calculate_body_shape(bust: int, waist: int, hips: int) -> str:
    """Calculate body shape from B/W/H (cm). Priority: Hourglass → Pear → Inv. Δ → Apple → Column."""
    if bust == 0 or hips == 0:
        return None

    if abs(bust - hips) <= 5 and bust - waist >= 18 and hips - waist >= 18:
        return "Hourglass"

    if hips - bust >= 6 and hips - waist >= 15:
        return "Pear"

    if bust - hips >= 6 and bust - waist >= 15:
        return "Inverted Triangle"

    if waist >= bust - 5 and waist >= hips - 5:
        return "Apple"

    return "Column"


_SHAPE_TO_CSV_BODY_PROPORTION = {
    "Pear": "Triangle",
    "Column": "Rectangle",
    "Inverted Triangle": "Inverted Triangle",
}


def _get_recommended_masters(preferred_style: str = None, goals: list = None) -> list:
    """
    Get recommended masters based on user preferences and goals.

    Algorithm:
    1. If preferred_style provided, search for masters with that keyword in description
    2. Based on goals:
       - hairstyle -> hairdressers, hair stylists
       - style -> stylists
       - makeup -> makeup artists, визажисти
       - nails -> nail masters
       - overall -> mix of specialists
    3. Fallback: first 3 active masters
    """
    from django.db.models import Q
    from masters.models import Master

    base_qs = Master.objects.filter(is_active=True).select_related('user')

    goal_keywords = {
        'hairstyle': ['hair', 'перукар', 'hairdresser', 'барбер', 'стрижка', 'зачіска'],
        'style': ['стиліст', 'stylist', 'імідж', 'image', 'стиль'],
        'makeup': ['візаж', 'makeup', 'макіяж', 'мейкап', 'візажист'],
        'nails': ['манікюр', 'nail', 'педикюр', 'нігт', 'manicure'],
        'overall': ['стиліст', 'візаж', 'манікюр', 'hair', 'beauty'],
    }

    style_keywords = {
        'vintage': ['вінтаж', 'vintage', 'ретро', 'retro', 'класик'],
        'street': ['street', 'вуличн', 'casual', 'кежуал'],
        'classic': ['класик', 'classic', 'елегант', 'elegant'],
        'minimalist': ['мінімал', 'minimal', 'простий', 'simple'],
        'bohemian': ['бохо', 'boho', 'етно', 'hippie'],
        'sporty': ['спорт', 'sport', 'фітнес', 'fitness', 'активн'],
        'glamorous': ['гламур', 'glamour', 'люкс', 'luxury', 'шик'],
        'romantic': ['романт', 'romantic', 'ніжн', 'feminine'],
    }

    found_masters = []

    if preferred_style:
        style_lower = preferred_style.lower()
        keywords = style_keywords.get(style_lower, [style_lower])
        style_filter = Q()
        for kw in keywords:
            style_filter |= Q(description__icontains=kw) | Q(specialization__icontains=kw)
        style_masters = list(base_qs.filter(style_filter).distinct()[:3])
        found_masters.extend(style_masters)

    if goals:
        for goal in goals:
            if len(found_masters) >= 3:
                break
            keywords = goal_keywords.get(goal, [])
            if not keywords:
                continue
            goal_filter = Q()
            for kw in keywords:
                goal_filter |= Q(description__icontains=kw) | Q(specialization__icontains=kw)
            goal_masters = list(base_qs.filter(goal_filter).exclude(
                id__in=[m.id for m in found_masters]
            ).distinct()[:2])
            found_masters.extend(goal_masters)

    if len(found_masters) < 3:
        remaining = 3 - len(found_masters)
        fallback = list(base_qs.exclude(
            id__in=[m.id for m in found_masters]
        ).order_by('-rating')[:remaining])
        found_masters.extend(fallback)

    result = []
    for m in found_masters[:3]:
        result.append({
            'id': m.id,
            'name': m.name,
            'specialization': m.specialization,
            'profile_photo': m.profile_photo or '',
            'rating': float(m.rating),
            'city': m.city or '',
        })
    return result


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
      preferred_style  — (optional) e.g. "vintage", "classic", "street"
      goals            — (optional) list, e.g. ["hairstyle", "makeup"]
      body_measurements — (optional) {"bust": 90, "waist": 70, "hips": 95}
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

    calculated_body_shape = None
    body_measurements = data.get('body_measurements')
    if body_measurements:
        bust = body_measurements.get('bust') or 0
        waist = body_measurements.get('waist') or 0
        hips = body_measurements.get('hips') or 0
        if bust > 0 and waist > 0 and hips > 0:
            calculated_body_shape = _calculate_body_shape(bust, waist, hips)
            if calculated_body_shape:
                csv_proportion = _SHAPE_TO_CSV_BODY_PROPORTION.get(
                    calculated_body_shape, calculated_body_shape
                )
                inputs['body_proportion'] = csv_proportion

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

    preferred_style = data.get('preferred_style')
    goals = data.get('goals')
    recommended_masters = _get_recommended_masters(preferred_style, goals)
    payload['recommended_masters'] = recommended_masters

    if calculated_body_shape:
        payload['calculated_body_shape'] = calculated_body_shape

    return JsonResponse(payload, safe=False)
