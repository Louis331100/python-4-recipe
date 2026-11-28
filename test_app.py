import os
import unittest
from unittest.mock import Mock, patch

from streamlit.testing.v1 import AppTest

import data_loader
import image_generator
import prompt_builder


class RecipeNavigationTests(unittest.TestCase):
    def test_result_view_can_regenerate_and_restore_form_values(self):
        menu = {
            "cookware": ["快煮鍋"],
            "categories": {"主食": ["白飯"]},
            "default_seasonings": ["鹽"],
            "recipe_preferences": ["快速料理"],
        }
        recipe = {
            "dish_name": "測試料理",
            "servings": 1,
            "time_minutes": 10,
            "preference": "快速料理",
            "cookware_used": ["快煮鍋"],
            "existing_ingredients": ["白飯"],
            "used_seasonings": ["鹽"],
            "suggested_purchases": [],
            "steps": [
                {
                    "step_number": 1,
                    "cookware": "快煮鍋",
                    "instruction": "加熱。",
                }
            ],
            "reminders": [],
        }
        generate_recipe = Mock(side_effect=[recipe, recipe])

        with patch.object(data_loader, "load_menu", return_value=menu), \
                patch.object(
                    prompt_builder,
                    "generate_recipe",
                    generate_recipe,
                ), \
                patch.object(
                    image_generator,
                    "generate_recipe_image",
                    return_value=None,
                ):
            app = AppTest.from_file(
                os.path.join(os.path.dirname(__file__), "app.py")
            ).run()
            app.multiselect(key="selected_cookware").select("快煮鍋")
            app.multiselect(key="category_主食").select("白飯")
            app.text_input(key="manual_ingredients").set_value("玉米")
            app.checkbox(key="allow_extra_buy").set_value(True)
            app.button[0].click().run()

            self.assertFalse(app.exception)
            self.assertIn(
                "regenerate_recipe",
                [button.key for button in app.button],
            )
            self.assertNotIn(
                "selected_cookware",
                [widget.key for widget in app.multiselect],
            )
            generate_recipe.assert_called_once()

            app.button(key="regenerate_recipe").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(generate_recipe.call_count, 2)

            app.button(key="return_to_recipe_form").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(
                app.multiselect(key="selected_cookware").value,
                ["快煮鍋"],
            )
            self.assertEqual(
                app.multiselect(key="category_主食").value,
                ["白飯"],
            )
            self.assertEqual(
                app.text_input(key="manual_ingredients").value,
                "玉米",
            )
            self.assertTrue(app.checkbox(key="allow_extra_buy").value)


if __name__ == "__main__":
    unittest.main()
