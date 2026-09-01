# language: en
@intelligent_reset @mobile_backend @end_to_end
Feature: Intelligent Reset End-to-End Execution, Resilience, and Physical Invariants
  As a Store Associate using the Store Intelligence Mobile App (Android & iOS)
  I want to reset modular shelves across multiple bays according to planogram specifications
  So that product facings are 100% compliant, foreign items are removed, and cart balance is preserved.

  Background:
    Given the associate is authenticated with valid credentials "vipin_nair"
    And the backend target instance is "https://epsilon.rebotics.net"
    And the target store is Store #30248 ("PET CAT CAN") with Planogram #4139874
    And the modular setup consists of 4 Bays ("Bay 1", "Bay 2", "Bay 3", "Bay 4")

  # =========================================================================
  # SCENARIO 1: FRESH END-TO-END INTELLIGENT RESET PIPELINE (FROM SCRATCH)
  # =========================================================================
  @fresh_run @full_pipeline
  Scenario: Associate performs complete end-to-end Intelligent Reset from initial photo capture to completion
    # Phase 1: Task Provisioning & Pre-Reset Shelf Scans
    Given the associate creates a new Intelligent Reset task on Epsilon QA
    When the associate captures and uploads high-resolution pre-reset shelf photos for:
      | Bay Number | Section ID | Image Source                             |
      | Bay 1      | 5454639    | test-data/images/bay_1_scan.jpg          |
      | Bay 2      | 5454638    | test-data/images/bay_2_scan.jpg          |
      | Bay 3      | 5454637    | test-data/images/bay_3_scan.jpg          |
      | Bay 4      | 5454636    | test-data/images/bay_4_scan.jpg          |
    And the associate waits for Hawkeye Computer Vision pipeline processing
    Then a task occurrence is generated with status "IN_PROGRESS"
    And 592 live action items are generated across all 4 bays

    # Phase 2: Action Queue Inspection & Partitioning
    When the mobile app retrieves the action list via "GET /api/v1/tasks/{id}/action-list/retailer/"
    Then the action items are partitioned into prioritized 3-layer execution sequence:
      | Priority | Action Type      | Mobile Visual Card      | Theme  | Total Expected |
      | 1        | ACTION_IDENTIFY  | 🔍 IDENTIFY FACING      | Orange | 213            |
      | 2        | ACTION_REMOVE    | 🗑️ REMOVE FROM SHELF    | Red    | 113            |
      | 3        | ACTION_SHIFT     | 🛒 SET ASIDE TO CART    | Orange | 64             |
      | 4        | ACTION_ADD       | ➕ ADD TO SHELF         | Green  | 258            |
      | 5        | ACTION_RESTOCK   | 📦 RESTOCK SHELF        | Green  | 8              |

    # Phase 3: Step-by-Step Mobile Action Execution
    When the associate inspects Bay 1 and scans an unreadable barcode for "Fancy Feast Medleys"
    And the associate clicks "✅ Complete Action"
    Then a "PATCH" request is sent with state "STATE_ACCEPTED"
    And the card drops from the mobile screen with an exit animation

    When the associate encounters foreign competitor items in Bay 1
    And the associate removes each foreign item and stages it onto the rolling cart
    Then the rolling cart ledger increases:
      | Cart Field | Balance |
      | FOREIGN    | +1      |

    When the associate encounters cross-bay items in Bay 1 intended for Bay 2
    And the associate picks the item to the rolling cart via card "🛒 SET ASIDE TO CART"
    Then the rolling cart ledger increases:
      | Cart Field | Balance |
      | POG PICKS  | +1      |

    When the associate moves to Bay 2 and executes "➕ ADD TO SHELF" from the rolling cart
    Then the rolling cart ledger decreases:
      | Cart Field | Balance |
      | POG PICKS  | -1      |

    # Phase 4: Final Task Completion
    When all 592 actions are completed across Bays 1, 2, 3, and 4
    Then the rolling cart balance has 0 remaining POG picks
    And the mobile screen displays "🎉 ALL ACTIONS COMPLETED"
    And the planogram compliance reaches 100%

  # =========================================================================
  # SCENARIO 2: FAST-LOAD EXISTING TASK ID (SKIP SCANNING)
  # =========================================================================
  @fast_load @skip_scanning
  Scenario: Associate loads an existing Task ID to skip photo scanning and CV wait times
    Given shelf scanning has already been completed manually for Task ID "27315261"
    When the user enters Task ID "27315261" on the runner dashboard
    And the user clicks "📥 Load Actions & Run Test"
    Then the runner directly fetches the action list via "POST /api/runner/load_task"
    And all 592 live actions are loaded in less than 1 second without image upload
    And the rolling cart ledger initializes with target forecasts:
      | Target Forecast | Count |
      | Foreign Target  | 113   |
      | Add Target      | 258   |
    And the associate can immediately step through physical actions

  # =========================================================================
  # SCENARIO 3: MID-RESET USER LOGOUT & DELAYED TASK RESUMPTION
  # =========================================================================
  @resilience @logout_resume
  Scenario: Associate logs out mid-reset and resumes task after 1 hour without losing cart or queue state
    Given the associate has loaded Task ID "27315261"
    And the associate has executed 50 actions:
      | Action Category  | Executed Count |
      | Foreign Removals | 20             |
      | Cross-Bay Picks  | 15             |
      | Shelf Additions  | 15             |
    And the rolling cart contains 20 foreign items and 0 pending picks
    When the associate logs out of the mobile app and closes the session
    And the associate waits for 1 hour
    And the associate logs back in with a fresh authentication token
    And the mobile app reloads Task ID "27315261"
    Then all 50 completed actions remain dropped from the active mobile stack
    And exactly 542 remaining actions are presented in correct priority sequence
    And the active card points to Step #51 without resetting to Step #1
    And the rolling cart balance is recovered:
      | Cart Category | Restored Balance |
      | FOREIGN       | 20               |
      | POG PICKS     | 0                |
    And zero actions are duplicated or misplaced across bays

  # =========================================================================
  # SCENARIO 4: MID-TASK IN-FLIGHT PULL-TO-REFRESH & NETWORK RECONNECT
  # =========================================================================
  @idempotency @network_resilience
  Scenario: Associate pulls down to refresh while completing an action without creating duplicate items
    Given the associate is actively executing Step #12 on Bay 2
    When the associate triggers a "PATCH" completion for Step #12
    And the associate simultaneously triggers "Pull-to-Refresh" on the mobile screen
    Then the backend processes the "STATE_ACCEPTED" transition idempotently
    And the mobile card for Step #12 drops from the UI stack
    And Step #13 becomes the active visible card
    And the rolling cart ledger is updated exactly once without duplicate counts

  # =========================================================================
  # SCENARIO 5: MISPLACED ITEM DETECTION & VALIDATION GUARD
  # =========================================================================
  @validation_guard @error_prevention
  Scenario: Associate attempts to place a cart item into incorrect bay coordinates
    Given the rolling cart has an item with UPC "050000578412" intended for "Bay 3, Shelf 2, Pos 4"
    When the associate scans barcode "050000578412" while standing at "Bay 1"
    Then the mobile validation guard detects a coordinate mismatch:
      | Expected Bay | Attempted Bay | Validation Status |
      | Bay 3        | Bay 1         | REJECTED ⛔       |
    And the mobile app displays an alert: "Bay Mismatch: Item belongs in Bay 3 (Shelf 2, Pos 4)"
    And the shelf placement is blocked until the associate scans the item in Bay 3

  # =========================================================================
  # SCENARIO 6: MULTI-DEVICE CROSS-PLATFORM HANDOFF (ANDROID TO IOS)
  # =========================================================================
  @cross_platform @parity
  Scenario: Android associate executes Bay 1, logs out; iOS associate logs in to continue Bay 2
    Given Associate "Alex" on Android (branch: intelligent-reset) executes all actions for Bay 1
    And Associate "Alex" logs out
    When Associate "Sarah" on iOS (branch: development) logs in and opens the same task
    Then the iOS app retrieves the latest backend state
    And all Bay 1 actions are excluded from the iOS active card stack
    And the iOS card stack starts seamlessly on Bay 2, Step #1
    And the rolling cart balance displayed on iOS matches the Android cart balance exactly
