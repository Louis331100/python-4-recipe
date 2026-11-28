import json
import os
import unittest
from unittest.mock import Mock, patch

from streamlit.testing.v1 import AppTest

import data_loader
import prompt_builder


class RecipeNavigationTests(unittest.TestCase):
    def test_result_view_can_regenerate_and_restore_form_values(self):
        menu = {
            "cookware": ["快煮鍋", "微波爐"],
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
        generate_recipe = Mock(side_effect=[recipe, recipe, recipe])

        with patch.object(data_loader, "load_menu", return_value=menu), \
                patch.object(
                    prompt_builder,
                    "generate_recipe",
                    generate_recipe,
                ):
            app = AppTest.from_file(
                os.path.join(os.path.dirname(__file__), "app.py")
            ).run()
            app.multiselect(key="selected_cookware").select("快煮鍋")
            app.multiselect(key="category_主食").select("白飯")
            app.text_input(key="manual_ingredients").set_value("玉米")
            app.checkbox(key="allow_extra_buy").set_value(True)
            app.button(
                key="FormSubmitter:recipe_input_form-✨ 生成食譜"
            ).click().run()

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
            app.multiselect(key="selected_cookware").set_value(["微波爐"])
            app.button(
                key="FormSubmitter:recipe_input_form-✨ 生成食譜"
            ).click().run()
            self.assertFalse(app.exception)
            latest_prompt = json.loads(generate_recipe.call_args.args[0])
            self.assertEqual(
                latest_prompt["conditions"]["cookware"],
                ["微波爐"],
            )

    def test_correcting_missing_cookware_does_not_restore_stale_empty_value(self):
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

        with patch.object(data_loader, "load_menu", return_value=menu), \
                patch.object(
                    prompt_builder,
                    "generate_recipe",
                    return_value=recipe,
                ) as generate_recipe:
            app = AppTest.from_file(
                os.path.join(os.path.dirname(__file__), "app.py")
            ).run()
            app.multiselect(key="category_主食").select("白飯")
            app.button(
                key="FormSubmitter:recipe_input_form-✨ 生成食譜"
            ).click().run()
            self.assertTrue(app.error)
            generate_recipe.assert_not_called()

            app.multiselect(key="selected_cookware").select("快煮鍋")
            app.button(
                key="FormSubmitter:recipe_input_form-✨ 生成食譜"
            ).click().run()
            self.assertFalse(app.exception)
            generate_recipe.assert_called_once()

    def test_random_challenge_selects_six_to_ten_with_four_ingredients(self):
        menu = {
            "cookware": ["快煮鍋", "微波爐"],
            "categories": {
                "主食": ["食材一", "食材二", "食材三", "食材四", "食材五", "食材六"],
                "其他調味料": ["調味一", "調味二", "調味三", "調味四"],
            },
            "default_seasonings": ["鹽", "醬油", "糖"],
            "recipe_preferences": ["快速料理"],
        }
        recipe = {
            "dish_name": "測試料理",
            "servings": 1,
            "time_minutes": 10,
            "preference": "快速料理",
            "cookware_used": ["微波爐"],
            "existing_ingredients": ["食材一"],
            "used_seasonings": ["鹽"],
            "suggested_purchases": [],
            "steps": [
                {
                    "step_number": 1,
                    "cookware": "微波爐",
                    "instruction": "加熱。",
                }
            ],
            "reminders": [],
        }

        with patch.object(data_loader, "load_menu", return_value=menu), \
                patch.object(
                    prompt_builder,
                    "generate_recipe",
                    return_value=recipe,
                ) as generate_recipe:
            app = AppTest.from_file(
                os.path.join(os.path.dirname(__file__), "app.py")
            ).run()
            app.button(key="random_ingredient_challenge").click().run()

            self.assertFalse(app.exception)
            ingredient_count = len(app.multiselect(key="category_主食").value)
            seasoning_count = (
                len(app.multiselect(key="category_其他調味料").value)
                + len(app.multiselect(key="selected_default_seasonings").value)
            )
            self.assertGreaterEqual(ingredient_count, 4)
            self.assertGreaterEqual(ingredient_count + seasoning_count, 6)
            self.assertLessEqual(ingredient_count + seasoning_count, 10)
            app.multiselect(key="selected_cookware").select("微波爐")
            app.button(
                key="FormSubmitter:recipe_input_form-✨ 生成食譜"
            ).click().run()
            self.assertFalse(app.exception)
            self.assertEqual(
                json.loads(generate_recipe.call_args.args[0])[
                    "conditions"
                ]["cookware"],
                ["微波爐"],
            )


if __name__ == "__main__":
    unittest.main()
