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


def _get_recommended_masters(
    preferred_style: str = None,
    goals: list = None,
    user_city: str = None,
    max_results: int = 12,
) -> list:
    """
    Recommend masters after the appearance test.

    1) If the user has a city: first list masters in that city who also match the
       selected work areas (goals) and preferred style (keyword hits in
       description/specialization). Sorted by relevance score, then rating.

    2) If there are none in (1), or to fill remaining slots: all other masters
       sorted by the same relevance (aspects) and rating — city is not required.

    When the user did not select goals or preferred_style, "aspect match" is
    treated as true for everyone, so ordering falls back to same-city first,
    then by rating within/between groups.
    """
    from masters.models import Master

    city_key = (user_city or '').strip().casefold()

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

    all_active = list(Master.objects.filter(is_active=True).select_related('user'))
    if not all_active:
        return []

    style_kws = []
    if preferred_style:
        style_kws = style_keywords.get(preferred_style.lower(), [preferred_style.lower()])

    goal_kws = []
    if goals:
        for g in goals:
            goal_kws.extend(goal_keywords.get(g, []))

    def keyword_hits(master, keywords):
        if not keywords:
            return 0
        haystack = f'{master.description or ""} {master.specialization or ""}'.lower()
        return sum(1 for kw in keywords if kw and kw in haystack)

    has_aspect_filters = bool(style_kws or goal_kws)

    ranked_rows = []
    for m in all_active:
        style_hits = keyword_hits(m, style_kws)
        goal_hits = keyword_hits(m, goal_kws)
        aspect_score = 8.0 * style_hits + min(15.0, 5.0 * goal_hits)
        if has_aspect_filters:
            matches_aspects = aspect_score > 0
        else:
            matches_aspects = True

        same_city = False
        if city_key:
            m_city = (m.city or '').strip().casefold()
            same_city = m_city == city_key

        ranked_rows.append({
            'm': m,
            'aspect_score': aspect_score,
            'same_city': same_city,
            'matches_aspects': matches_aspects,
        })

    def sort_aspects_then_rating(row):
        m = row['m']
        return (
            -row['aspect_score'],
            -float(m.rating or 0.0),
            -(m.review_count or 0),
            m.name or '',
        )

    tier_local_relevant = [
        r for r in ranked_rows
        if r['same_city'] and r['matches_aspects']
    ]
    tier_local_relevant.sort(key=sort_aspects_then_rating)

    local_ids = {r['m'].id for r in tier_local_relevant}
    tier_rest = [r for r in ranked_rows if r['m'].id not in local_ids]
    tier_rest.sort(key=sort_aspects_then_rating)

    if not tier_local_relevant:
        ordered_masters = [r['m'] for r in tier_rest]
    else:
        ordered_masters = [r['m'] for r in tier_local_relevant + tier_rest]

    result = []
    for m in ordered_masters[:max_results]:
        result.append({
            'id': m.id,
            'name': m.name,
            'specialization': m.specialization,
            'profile_photo': m.profile_photo or '',
            'rating': float(m.rating or 0.0),
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
    user_city = str(data.get('user_city', '')).strip()
    recommended_masters = _get_recommended_masters(
        preferred_style, goals, user_city=user_city or None,
    )
    payload['recommended_masters'] = recommended_masters

    if calculated_body_shape:
        payload['calculated_body_shape'] = calculated_body_shape

    return JsonResponse(payload, safe=False)
