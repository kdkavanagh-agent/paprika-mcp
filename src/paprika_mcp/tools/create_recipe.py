"""Create recipe tool - adds a new recipe to Paprika."""

from typing import Any

from mcp.types import TextContent
from paprika_recipes.remote import RemoteRecipe

from ..utils import get_categories, get_remote, translate_category_uids


def _as_text(value: Any) -> str:
    """Coerce a string or list-of-strings into a newline-separated string.

    Paprika stores multi-line fields (ingredients, directions) as a single
    newline-delimited string, so accept either shape from the caller for
    ergonomics and normalize to that representation.
    """
    if value is None:
        return ""
    if isinstance(value, list):
        return "\n".join(str(item).strip() for item in value if str(item).strip())
    return str(value)


async def create_recipe_tool(args: dict[str, Any]) -> list[TextContent]:
    """Create a new recipe in Paprika from the provided fields."""
    name = (args.get("name") or "").strip()
    if not name:
        return [TextContent(type="text", text="Error: 'name' is required")]

    remote = get_remote()

    # Resolve category names to UUIDs before creating anything so an unknown
    # category aborts cleanly without leaving a half-created recipe.
    category_uids: list[str] = []
    category_names = args.get("categories") or []
    if category_names:
        categories_info = get_categories(remote.bearer_token)
        name_to_uid = categories_info["name_to_uid"]
        for cat_name in category_names:
            cat_name = str(cat_name).strip()
            if not cat_name:
                continue
            uid = name_to_uid.get(cat_name.lower())
            if not uid:
                return [
                    TextContent(
                        type="text",
                        text=(
                            f"Error: Category '{cat_name}' not found in Paprika. "
                            "Use list_categories to see valid names. No recipe was created."
                        ),
                    )
                ]
            category_uids.append(uid)

    # Build the recipe. RemoteRecipe auto-generates uid, hash, and created.
    recipe = RemoteRecipe(
        name=name,
        ingredients=_as_text(args.get("ingredients")),
        directions=_as_text(args.get("directions")),
        description=args.get("description") or "",
        notes=args.get("notes") or "",
        categories=category_uids,
        source=args.get("source") or "",
        source_url=args.get("source_url") or "",
        prep_time=args.get("prep_time") or "",
        cook_time=args.get("cook_time") or "",
        total_time=args.get("total_time") or "",
        servings=args.get("servings") or "",
        difficulty=args.get("difficulty") or "",
        rating=int(args.get("rating") or 0),
        nutritional_info=args.get("nutritional_info") or "",
        image_url=args.get("image_url") or "",
    )

    try:
        remote.upload_recipe(recipe)
        # Ask Paprika to push the new recipe to connected apps/devices.
        remote.notify()
    except Exception as e:
        return [
            TextContent(
                type="text",
                text=f"Error creating recipe '{name}': {str(e)}",
            )
        ]

    category_display = (
        translate_category_uids(category_uids, remote.bearer_token)
        if category_uids
        else "(none)"
    )
    return [
        TextContent(
            type="text",
            text=(
                f"Successfully created recipe '{name}'\n"
                f"UID: {recipe.uid}\n"
                f"Categories: {category_display}"
            ),
        )
    ]


# Tool definition
TOOL_DEFINITION = {
    "name": "create_recipe",
    "description": (
        "Create a new recipe in Paprika. Only 'name' is required; all other "
        "fields are optional. The recipe is stored using Paprika's native "
        "structure and a unique ID is generated automatically.\n\n"
        "FIELD NOTES:\n"
        "  - ingredients: one ingredient per line. Accepts a single string "
        "(newline-separated) or an array of strings. Paprika groups ingredients "
        "under a header by putting a blank line then a bare header line "
        "(e.g. 'For the sauce:') before that group's ingredients.\n"
        "  - directions: cooking steps. Accepts a single string (newline- or "
        "blank-line-separated) or an array of strings, one step per element.\n"
        "  - categories: array of existing category NAMES (not UUIDs). Unknown "
        "names abort creation — use list_categories to find valid names.\n"
        "  - rating: integer 0-5.\n"
        "  - times (prep_time/cook_time/total_time) and servings are free-form "
        "text (e.g. '30 min', '4 servings')."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Recipe title (required)"},
            "ingredients": {
                "type": ["string", "array"],
                "items": {"type": "string"},
                "description": "Ingredients, one per line (string) or array of lines",
            },
            "directions": {
                "type": ["string", "array"],
                "items": {"type": "string"},
                "description": "Cooking steps (string) or array of steps",
            },
            "description": {"type": "string", "description": "Short summary"},
            "notes": {"type": "string", "description": "Additional notes"},
            "categories": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Existing category names (converted to UUIDs)",
            },
            "source": {
                "type": "string",
                "description": "Source (cookbook name, website, etc.)",
            },
            "source_url": {"type": "string", "description": "URL of the recipe"},
            "prep_time": {"type": "string", "description": "Prep time, e.g. '15 min'"},
            "cook_time": {"type": "string", "description": "Cook time, e.g. '30 min'"},
            "total_time": {"type": "string", "description": "Total time"},
            "servings": {"type": "string", "description": "Servings, e.g. '4'"},
            "difficulty": {
                "type": "string",
                "description": "Difficulty, e.g. 'Easy'",
            },
            "rating": {
                "type": "integer",
                "minimum": 0,
                "maximum": 5,
                "description": "Rating 0-5",
            },
            "nutritional_info": {
                "type": "string",
                "description": "Nutritional information",
            },
            "image_url": {
                "type": "string",
                "description": "URL of a recipe image",
            },
        },
        "required": ["name"],
    },
}
