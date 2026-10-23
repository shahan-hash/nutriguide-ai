# TEST RESULTS

These results were produced by actually running the tests in this project (not estimated).

## How they were run

* Command: `python -m unittest discover -s tests -t . -v`
* Environment of the run: Linux sandbox, Python 3.12, pandas / numpy / scipy / scikit-learn from the
  sandbox, Streamlit **1.62.0** (the version found in the uploaded `venv`).
* All tests use the REAL files in `data/processed` (7,793 USDA SR Legacy rows / 7,448 after safety
  constraints). History tests use a temporary SQLite file (never your real history).
* Tests marked **synthetic** use hand-made rows on purpose (to test arithmetic and bad values).

Result of the final run: **Ran 58 tests - OK**
(58 tests: 48 logic tests + 10 end-to-end app tests).

## What each test group covers

| Group (file) | Tests | What is checked |
|---|---|---|
| Nutrition (`test_nutrition.py`) | 8 | per-100 g -> grams conversion (synthetic row), missing / NaN / negative / zero values (synthetic), meal total = sum of foods and not rounded, dataset energy used directly, daily = sum of meals, meal targets add up to the daily target, coverage % and gap, Target-vs-Planned statuses, independent verification catches a tampered value |
| Calorie target (`test_calorie_target.py`) | 9 | Lunch 1000 kcal, Dinner 1000 kcal, Breakfast target, custom 876 kcal, custom daily split 25/40/35, best-ranked candidate wins (weak candidates exist and are rejected), infeasible target reported honestly (no faked %), realistic portions, full pipeline |
| Available foods (`test_available_foods.py`) | 9 | only the four selected foods in every meal for 1-4 dishes, full pipeline never adds oats/chicken/egg, replacement + regeneration never add foods, shortfall explained when foods cannot reach the target, "not found" vs "blocked by diet" explained, allergy filter still active, vegetarian excludes egg, duplicate typed food = one dish |
| Dish limit (`test_dish_limit.py`) | 5 | limits 1/2/3/4 never exceeded (generation, replacement, full pipeline), limit not silently overridden, bigger portion is not a new dish |
| Replace meal (`test_replace.py`) | 6 | replace Breakfast / Lunch / Dinner: the other two meals are exactly identical (foods and grams), different food combination, totals + coverage recalculated, repeated clicks cycle through alternatives, no alternative -> original kept with a message, empty pool does not crash |
| Profiles & history (`test_profiles_history.py`) | 8 | missing DB / empty history safe, new profile settings round-trip, history survives a restart (separate Python process), two profiles never mix, 10-day vs 15-day windows (backdated rows), update-in-place without duplicates, history gives variety with fit within 6 points, history cannot force other foods |
| Public demo mode (`test_public_mode.py`) | 2 | two visitors never see each other's profiles in public mode; a visitor keeps their own profile during the session |
| Extras (`test_extras.py`) | 4 | household measures (roti / katori / egg / glass, blank for unknown foods or bad input, display only), download button + split bars + approx. measures render without errors |
| App end-to-end (`test_app.py`) | 7 | real `app.py` run with Streamlit AppTest: first load, custom 876 kcal lunch, strict foods, Replace Breakfast/Lunch/Dinner without any exception (the old NameError scenario) and with other meals unchanged, dish-limit selector, two profiles keep separate settings/history, 10 vs 15 days + variety on regenerate, strict mode OFF message |

## Real example output (pantry: Rice, Dal, Paneer proxy, Roti; targets B 600 / L 1000 / D 1000)

```
Pantry: Rice, Dal, Paneer(proxy), Roti | targets B600 / L1000 / D1000

max dishes = 1
  Breakfast target    600  planned   594.0 kcal  coverage  99.0%  [Roti 200 g]
  Lunch     target   1000  planned   594.0 kcal  coverage  59.4%  [Roti 200 g]
     note: With at most 1 dish(es) from the allowed foods, realistic portion limits allow about 594 kcal, so this meal is 406 kcal short of its 1000 kcal target.
     note: Allowing 2 dishes could reach about 1000 kcal.
  Dinner    target   1000  planned   594.0 kcal  coverage  59.4%  [Roti 200 g]
     note: With at most 1 dish(es) from the allowed foods, realistic portion limits allow about 594 kcal, so this meal is 406 kcal short of its 1000 kcal target.
     note: Allowing 2 dishes could reach about 1000 kcal.

max dishes = 2
  Breakfast target    600  planned   594.0 kcal  coverage  99.0%  [Roti 200 g]
  Lunch     target   1000  planned   999.6 kcal  coverage 100.0%  [Rice 312 g, Roti 200 g]
  Dinner    target   1000  planned   994.7 kcal  coverage  99.5%  [Paneer 134 g, Roti 200 g]

max dishes = 3
  Breakfast target    600  planned   594.0 kcal  coverage  99.0%  [Roti 200 g]
  Lunch     target   1000  planned   999.9 kcal  coverage 100.0%  [Rice 346 g, Paneer 30 g, Roti 155 g]
  Dinner    target   1000  planned   999.1 kcal  coverage  99.9%  [Rice 347 g, Dal 50 g, Roti 165 g]

max dishes = 4
  Breakfast target    600  planned   594.0 kcal  coverage  99.0%  [Roti 200 g]
  Lunch     target   1000  planned   999.9 kcal  coverage 100.0%  [Rice 346 g, Paneer 30 g, Roti 155 g]
  Dinner    target   1000  planned   999.1 kcal  coverage  99.9%  [Rice 347 g, Dal 50 g, Roti 165 g]

Pantry: Rice + Dal only, max 2 dishes
  Breakfast target    600  planned   597.7 kcal  coverage  99.6%  [rice 350 g, dal 123 g]
  Lunch     target   1000  planned   861.0 kcal  coverage  86.1%  [rice 350 g, dal 350 g]
     note: With at most 2 dish(es) from the allowed foods, realistic portion limits allow about 861 kcal, so this meal is 139 kcal short of its 1000 kcal target.
     note: Add more available foods to close the gap.
  Dinner    target   1000  planned   861.0 kcal  coverage  86.1%  [rice 350 g, dal 350 g]
     note: With at most 2 dish(es) from the allowed foods, realistic portion limits allow about 861 kcal, so this meal is 139 kcal short of its 1000 kcal target.
     note: Add more available foods to close the gap.
```

Custom 876 kcal lunch through the real app (targets B 500 / L 876 / D 1000, same four foods, 3 dishes):

```
Breakfast  500 kcal target -> 499 kcal planned (99.8%)  Roti 168 g
Lunch      876 kcal target -> 876 kcal planned (100.0%) Roti 151 g, Cooked White Rice 260 g, Paneer(proxy) 30 g
Dinner    1000 kcal target -> 999 kcal planned (99.9%)  Dal 50 g, Roti 200 g, Cooked White Rice 267 g
```

## Old code vs new code (calorie accuracy, measured with `evaluate.py`)

Same random profiles (seed 2026, 12 profiles x 3 meals) run on the first version of the project and on the current version.

| Mode | Code | Mean error | Meals within 5% |
|---|---|---|---|
| Common foods | first version | 16.4% | 25.0% |
| Common foods | current | 0.1% | 100% |
| 8 typed foods | first version | 6.7% | 52.8% |
| 8 typed foods | current | 1.1% | 94.4% |

Small sample, calories only; see the README (Tests and evaluation).

## Also done

* `python -m compileall` on every project file: OK.
* The meal history database is created automatically when missing (tested from a non-existent path).

## Limitations of this testing (honest list)

* The Streamlit tests run the real script headlessly (Streamlit's `AppTest`). **No real browser was used**,
  so the visual layout / CSS was not checked by eye.
* The sandbox is Linux; the Windows PowerShell commands in `README.md` were not executed by me. They are
  the standard venv / pip / streamlit commands.
* In the sandbox `pyarrow` could not be loaded, so the app renders its tables as plain HTML
  (which also means the app does not depend on pyarrow).
* The tests prove the numbers are calculated and verified consistently. They do not prove that
  USDA values are nutritionally perfect, that proxies (paneer = mozzarella) match your home food, or
  that allergen filtering is complete.

## Full verbose log of the final run

```
ok
ok
ok
ok
ok
ok
ok
test_allergy_filter_still_applies_in_pantry_mode (tests.test_available_foods.StrictPantry.test_allergy_filter_still_applies_in_pantry_mode) ... ok
test_every_dish_comes_from_the_four_foods_in_all_meals (tests.test_available_foods.StrictPantry.test_every_dish_comes_from_the_four_foods_in_all_meals) ... ok
test_four_foods_cannot_reach_target_reports_shortfall_without_extra_foods (tests.test_available_foods.StrictPantry.test_four_foods_cannot_reach_target_reports_shortfall_without_extra_foods) ... ok
test_four_foods_match_expected_usda_rows (tests.test_available_foods.StrictPantry.test_four_foods_match_expected_usda_rows) ... ok
test_full_pipeline_never_adds_unselected_foods (tests.test_available_foods.StrictPantry.test_full_pipeline_never_adds_unselected_foods) ... ok
test_replacement_and_regeneration_never_add_unselected_foods (tests.test_available_foods.StrictPantry.test_replacement_and_regeneration_never_add_unselected_foods) ... ok
test_same_food_typed_twice_is_one_dish (tests.test_available_foods.StrictPantry.test_same_food_typed_twice_is_one_dish) ... ok
test_unknown_food_and_blocked_food_are_explained (tests.test_available_foods.StrictPantry.test_unknown_food_and_blocked_food_are_explained) ... ok
test_vegetarian_excludes_eggs_but_eggetarian_allows (tests.test_available_foods.StrictPantry.test_vegetarian_excludes_eggs_but_eggetarian_allows) ... ok
test_any_custom_number_876 (tests.test_calorie_target.CalorieTargets.test_any_custom_number_876) ... ok
test_best_candidate_is_chosen_not_first_acceptable (tests.test_calorie_target.CalorieTargets.test_best_candidate_is_chosen_not_first_acceptable)
The winner has the smallest calorie error among all ranked candidates. ... ok
test_breakfast_target (tests.test_calorie_target.CalorieTargets.test_breakfast_target) ... ok
test_custom_daily_target_is_split_25_40_35 (tests.test_calorie_target.CalorieTargets.test_custom_daily_target_is_split_25_40_35) ... ok
test_dinner_1000_kcal (tests.test_calorie_target.CalorieTargets.test_dinner_1000_kcal) ... ok
test_end_to_end_with_real_pipeline_and_safety (tests.test_calorie_target.CalorieTargets.test_end_to_end_with_real_pipeline_and_safety) ... ok
test_lunch_1000_kcal (tests.test_calorie_target.CalorieTargets.test_lunch_1000_kcal) ... ok
test_no_faked_percentage_when_infeasible (tests.test_calorie_target.CalorieTargets.test_no_faked_percentage_when_infeasible) ... ok
test_portions_are_realistic (tests.test_calorie_target.CalorieTargets.test_portions_are_realistic) ... ok
test_larger_portion_is_not_a_new_dish (tests.test_dish_limit.DishLimit.test_larger_portion_is_not_a_new_dish) ... ok
test_limit_in_full_pipeline_broad_mode (tests.test_dish_limit.DishLimit.test_limit_in_full_pipeline_broad_mode) ... ok
test_limit_is_not_silently_overridden_to_reach_target (tests.test_dish_limit.DishLimit.test_limit_is_not_silently_overridden_to_reach_target) ... ok
test_limit_never_exceeded_in_generation (tests.test_dish_limit.DishLimit.test_limit_never_exceeded_in_generation) ... ok
test_limit_respected_by_replacement (tests.test_dish_limit.DishLimit.test_limit_respected_by_replacement) ... ok
ok
test_common_measures (tests.test_extras.HouseholdMeasures.test_common_measures) ... ok
test_measures_never_change_the_stored_grams (tests.test_extras.HouseholdMeasures.test_measures_never_change_the_stored_grams) ... ok
test_unknown_food_or_bad_input_gives_blank (tests.test_extras.HouseholdMeasures.test_unknown_food_or_bad_input_gives_blank) ... ok
test_compare_with_targets (tests.test_nutrition.NutritionMath.test_compare_with_targets) ... ok
test_custom_meal_targets_sum_and_coverage_gap (tests.test_nutrition.NutritionMath.test_custom_meal_targets_sum_and_coverage_gap) ... ok
test_daily_equals_sum_of_meals_and_meal_targets_sum_to_daily (tests.test_nutrition.NutritionMath.test_daily_equals_sum_of_meals_and_meal_targets_sum_to_daily) ... ok
test_dataset_values_used_directly (tests.test_nutrition.NutritionMath.test_dataset_values_used_directly) ... ok
test_meal_total_equals_sum_of_foods_and_is_not_rounded (tests.test_nutrition.NutritionMath.test_meal_total_equals_sum_of_foods_and_is_not_rounded) ... ok
test_missing_and_bad_values_are_safe (tests.test_nutrition.NutritionMath.test_missing_and_bad_values_are_safe) ... ok
test_per_100g_to_portion (tests.test_nutrition.NutritionMath.test_per_100g_to_portion) ... ok
test_verification_independent_recalculation (tests.test_nutrition.NutritionMath.test_verification_independent_recalculation) ... ok
test_10_and_15_day_windows (tests.test_profiles_history.ProfilesAndHistory.test_10_and_15_day_windows) ... ok
test_history_cannot_force_unavailable_or_unsafe_foods (tests.test_profiles_history.ProfilesAndHistory.test_history_cannot_force_unavailable_or_unsafe_foods)
With only two foods, history must allow reusing them. ... ok
test_history_encourages_variety_without_harming_fit (tests.test_profiles_history.ProfilesAndHistory.test_history_encourages_variety_without_harming_fit) ... ok
test_history_survives_application_restart (tests.test_profiles_history.ProfilesAndHistory.test_history_survives_application_restart) ... ok
test_missing_database_and_empty_history_are_safe (tests.test_profiles_history.ProfilesAndHistory.test_missing_database_and_empty_history_are_safe) ... ok
test_new_profile_settings_roundtrip (tests.test_profiles_history.ProfilesAndHistory.test_new_profile_settings_roundtrip) ... ok
test_two_profiles_never_mix (tests.test_profiles_history.ProfilesAndHistory.test_two_profiles_never_mix) ... ok
test_update_plan_replaces_row_not_duplicates (tests.test_profiles_history.ProfilesAndHistory.test_update_plan_replaces_row_not_duplicates) ... ok
ok
ok
test_compat_wrapper (tests.test_replace.ReplaceMeal.test_compat_wrapper) ... ok
test_empty_pool_does_not_crash (tests.test_replace.ReplaceMeal.test_empty_pool_does_not_crash) ... ok
test_no_alternative_keeps_original_and_explains (tests.test_replace.ReplaceMeal.test_no_alternative_keeps_original_and_explains) ... ok
test_repeated_clicks_cycle_through_different_combinations (tests.test_replace.ReplaceMeal.test_repeated_clicks_cycle_through_different_combinations) ... ok
test_replace_each_meal_leaves_other_two_exactly_unchanged (tests.test_replace.ReplaceMeal.test_replace_each_meal_leaves_other_two_exactly_unchanged) ... ok
test_totals_are_recalculated_after_replacement (tests.test_replace.ReplaceMeal.test_totals_are_recalculated_after_replacement) ... ok

----------------------------------------------------------------------
Ran 58 tests in 23.918s

OK
```
