import json
import os
import unittest
from unittest.mock import Mock, patch

import streamlit as st
from streamlit.testing.v1 import AppTest

import data_loader
import prompt_builder


class RecipeNavigationTests(unittest.TestCase):
    def test_result_view_can_regenerate_and_restore_form_values(self):
        menu = {
            "cookware": ["快煮鍋", "微波爐"],
            "categories": {"主食": ["白飯"]},
            "default_seasonings": ["鹽", "醬油"],
            "recipe_preferences": ["快速料理"],
        }
        recipe = {
            "dish_name": "測試料理",
            "servings": 1,
            "time_minutes": 10,
            "preference": "快速料理",
            "cookware_used": ["快煮鍋"],
            "existing_ingredients": ["白飯"],
            "ingredient_quantities": {
                "白飯": {
                    "grams": 150,
                    "milliliters": None,
                    "is_liquid": False,
                }
            },
            "used_seasonings": ["鹽", "醬油"],
            "seasoning_quantities": {
                "鹽": {
                    "grams": 2,
                    "milliliters": None,
                    "is_liquid": False,
                },
                "醬油": {
                    "grams": 5,
                    "milliliters": 5,
                    "is_liquid": True,
                },
            },
            "suggested_purchases": [],
            "steps": [
                {
                    "step_number": 1,
                    "cookware": "快煮鍋",
                    "instruction": "加熱。",
                },
                {
                    "step_number": 2,
                    "cookware": "快煮鍋",
                    "instruction": "盛盤。",
                }
            ],
            "reminders": [],
        }
        generation_views = []

        def generate_recipe_during_current_view(prompt):
            generation_views.append(st.session_state.get("current_view"))
            return recipe

        generate_recipe = Mock(side_effect=generate_recipe_during_current_view)

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
            self.assertEqual(generation_views, ["generating"])
            self.assertIn(
                "regenerate_recipe",
                [button.key for button in app.button],
            )
            self.assertNotIn(
                "selected_cookware",
                [widget.key for widget in app.multiselect],
            )
            subheaders = [element.value for element in app.subheader]
            self.assertIn("使用食材", subheaders)
            self.assertIn("食譜步驟", subheaders)
            self.assertIn("注意事項", subheaders)
            markdown_text = "\n".join(
                element.value for element in app.markdown
            )
            self.assertIn("150 g", markdown_text)
            self.assertIn("5 g · 5 mL", markdown_text)
            self.assertIn("background: #3b3733", markdown_text)
            self.assertIn("color: #f5f0e9", markdown_text)
            self.assertIn(
                ".st-key-recipe_notes_card [data-testid=\"stMarkdownContainer\"] *",
                markdown_text,
            )
            self.assertNotIn("recipe_step_", markdown_text)
            self.assertIn("#### 步驟 1", markdown_text)
            self.assertIn("#### 步驟 2", markdown_text)
            self.assertIn("font-size: 1.1rem", markdown_text)
            self.assertIn(".st-key-recipe_steps hr", markdown_text)
            generate_recipe.assert_called_once()

            app.button(key="regenerate_recipe").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(generate_recipe.call_count, 2)
            self.assertEqual(generation_views, ["generating", "recipe"])

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
            self.assertEqual(
                generation_views,
                ["generating", "recipe", "generating"],
            )
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
            "ingredient_quantities": {
                "白飯": {
                    "grams": 150,
                    "milliliters": None,
                    "is_liquid": False,
                }
            },
            "used_seasonings": ["鹽"],
            "seasoning_quantities": {
                "鹽": {
                    "grams": 2,
                    "milliliters": None,
                    "is_liquid": False,
                }
            },
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

    def test_generation_failure_returns_to_saved_selection_view(self):
        menu = {
            "cookware": ["快煮鍋"],
            "categories": {"主食": ["白飯"]},
            "default_seasonings": ["鹽"],
            "recipe_preferences": ["快速料理"],
        }
        generate_recipe = Mock(
            side_effect=RuntimeError(
                "Gemini API 呼叫失敗：503 UNAVAILABLE"
            )
        )

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
            app.button(
                key="FormSubmitter:recipe_input_form-✨ 生成食譜"
            ).click().run()

            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["current_view"], "form")
            self.assertEqual(len(app.error), 1)
            generate_recipe.assert_called_once()
            self.assertEqual(
                app.multiselect(key="selected_cookware").value,
                ["快煮鍋"],
            )
            self.assertEqual(
                app.multiselect(key="category_主食").value,
                ["白飯"],
            )

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
            "ingredient_quantities": {
                "食材一": {
                    "grams": 100,
                    "milliliters": None,
                    "is_liquid": False,
                }
            },
            "used_seasonings": ["鹽"],
            "seasoning_quantities": {
                "鹽": {
                    "grams": 2,
                    "milliliters": None,
                    "is_liquid": False,
                }
            },
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
            extra_seasoning_count = len(
                app.multiselect(key="category_其他調味料").value
            )
            self.assertEqual(
                app.multiselect(key="selected_default_seasonings").value,
                menu["default_seasonings"],
            )
            self.assertGreaterEqual(ingredient_count, 4)
            self.assertGreaterEqual(
                ingredient_count + extra_seasoning_count,
                6,
            )
            self.assertLessEqual(
                ingredient_count + extra_seasoning_count,
                10,
            )
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
