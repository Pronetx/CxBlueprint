"""
QA Test: Lex Bot - Conversational Bot with Multiple Intents

Builds a flow that connects a caller to a Lex V2 bot and routes based on
recognized intents:

  welcome -> lex bot -> OrderStatus intent  -> order lookup -> disconnect
                     -> ReturnItem intent   -> return process -> disconnect
                     -> SpeakToAgent intent -> transfer msg -> disconnect
                     -> (error/fallback)    -> error msg -> disconnect

Tests:
  - lex_bot() convenience method
  - LexV2Bot type import from cxblueprint.blocks.types
  - on_intent() routing for multiple intents
  - Error handling on Lex block
  - Discoverability probes for alternative method names and import paths
"""

import sys
sys.path.insert(0, "src")
sys.path.insert(0, "qa_tests")

import os
import json
import traceback
from qa_helpers import QAReport, print_report


def run_test() -> QAReport:
    report = QAReport("test_lex_bot")

    # ----------------------------------------------------------------
    # Phase 1: Import verification
    # ----------------------------------------------------------------
    try:
        from cxblueprint import Flow
        report.success("Import Flow from cxblueprint")
    except Exception as e:
        report.error("Failed to import Flow from cxblueprint", e)
        return report

    # Import LexV2Bot -- test multiple import paths
    # Path 1: from cxblueprint.blocks.types (documented in API reference)
    try:
        from cxblueprint.blocks.types import LexV2Bot as LexV2Bot_types
        report.success("Import LexV2Bot from cxblueprint.blocks.types")
    except Exception as e:
        report.error("Failed to import LexV2Bot from cxblueprint.blocks.types", e)

    # Path 2: from cxblueprint directly (re-exported in __init__.py)
    try:
        from cxblueprint import LexV2Bot
        report.success(
            "Import LexV2Bot from cxblueprint (top-level re-export)",
            "This is the shorter, more convenient import path.",
        )
    except Exception as e:
        report.discoverability(
            "from cxblueprint import LexV2Bot",
            "from cxblueprint.blocks.types import LexV2Bot",
            f"Top-level import failed: {e}",
        )
        # Fall back to the deeper import
        try:
            from cxblueprint.blocks.types import LexV2Bot
        except Exception as e2:
            report.error("Failed to import LexV2Bot from any path", e2)
            return report

    # ----------------------------------------------------------------
    # Phase 2: Discoverability probes
    # ----------------------------------------------------------------
    flow_probe = Flow.build("Probe Flow")

    report.probe_method(flow_probe, "chatbot", "lex_bot")
    report.probe_method(flow_probe, "lex", "lex_bot")
    report.probe_method(flow_probe, "bot", "lex_bot")

    # Probe: can ConnectParticipantWithLexBot be imported from cxblueprint directly?
    try:
        from cxblueprint import ConnectParticipantWithLexBot
        report.discoverability(
            "from cxblueprint import ConnectParticipantWithLexBot",
            "from cxblueprint.blocks.participant_actions import ConnectParticipantWithLexBot",
            "Top-level import not available -- must use deep import path if "
            "using flow.add() instead of flow.lex_bot().",
        )
    except ImportError:
        report.discoverability(
            "from cxblueprint import ConnectParticipantWithLexBot",
            "from cxblueprint.blocks.participant_actions import ConnectParticipantWithLexBot",
            "ConnectParticipantWithLexBot is not re-exported from the top-level "
            "cxblueprint module. However, flow.lex_bot() convenience method "
            "eliminates the need for direct import in most cases.",
        )

    # ----------------------------------------------------------------
    # Phase 3: Build the Lex bot flow
    # ----------------------------------------------------------------
    try:
        flow = Flow.build("Customer Service Lex Bot")
        report.success("Flow.build() created flow instance")
    except Exception as e:
        report.error("Flow.build() failed", e)
        return report

    # Step 1: Welcome prompt
    try:
        welcome = flow.play_prompt(
            "Welcome to Acme customer service. I will connect you with our "
            "virtual assistant who can help with orders, returns, or connect "
            "you with a live agent."
        )
        report.success("play_prompt() created welcome block")
    except Exception as e:
        report.error("play_prompt() failed for welcome", e)
        return report

    # Step 2: Create Lex V2 Bot configuration
    try:
        bot_config = LexV2Bot(
            alias_arn="arn:aws:lex:us-east-1:123456789012:bot-alias/BOTID/ALIASID"
        )
        report.success(
            "LexV2Bot() created bot configuration",
            f"alias_arn={bot_config.alias_arn}",
        )
    except Exception as e:
        report.error("LexV2Bot() construction failed", e)
        return report

    # Step 3: Create Lex bot block using convenience method
    try:
        lex_block = flow.lex_bot(
            text="How can I help you today? You can ask about order status, "
                 "request a return, or ask to speak with an agent.",
            lex_v2_bot=bot_config,
        )
        report.success(
            "lex_bot() created ConnectParticipantWithLexBot block",
            f"type={lex_block.type}",
        )
    except Exception as e:
        report.error("lex_bot() convenience method failed", e)
        return report

    # Step 4: Create intent handler blocks
    try:
        order_status_msg = flow.play_prompt(
            "Let me look up your order. I am pulling your information now."
        )
        return_item_msg = flow.play_prompt(
            "I can help you with a return. Let me start the return process."
        )
        speak_agent_msg = flow.play_prompt(
            "I will connect you with a live agent. Please hold."
        )
        fallback_msg = flow.play_prompt(
            "I am sorry, I did not understand your request. Let me connect you "
            "with an agent who can help."
        )
        timeout_msg = flow.play_prompt(
            "I did not hear a response. Goodbye."
        )
        error_msg = flow.play_prompt(
            "We are experiencing technical difficulties with our virtual "
            "assistant. Please try again later."
        )
        report.success("Created 6 intent/error handler message blocks")
    except Exception as e:
        report.error("Failed to create intent handler blocks", e)
        return report

    # Step 5: Disconnect blocks
    try:
        disconnect_order = flow.disconnect()
        disconnect_return = flow.disconnect()
        disconnect_agent = flow.disconnect()
        disconnect_fallback = flow.disconnect()
        disconnect_timeout = flow.disconnect()
        disconnect_error = flow.disconnect()
        report.success("Created 6 disconnect blocks")
    except Exception as e:
        report.error("Failed to create disconnect blocks", e)
        return report

    # ----------------------------------------------------------------
    # Phase 4: Wire the flow
    # ----------------------------------------------------------------

    # Welcome -> Lex Bot
    try:
        welcome.then(lex_block)
        report.success("Wired welcome -> lex_bot")
    except Exception as e:
        report.error("welcome.then(lex_block) failed", e)
        return report

    # Lex Bot intent routing using on_intent()
    try:
        lex_block.on_intent("OrderStatus", order_status_msg)
        report.success(
            "on_intent('OrderStatus', ...) added intent condition",
        )
    except Exception as e:
        report.error("on_intent('OrderStatus', ...) failed", e)
        return report

    try:
        lex_block.on_intent("ReturnItem", return_item_msg)
        report.success("on_intent('ReturnItem', ...) added intent condition")
    except Exception as e:
        report.error("on_intent('ReturnItem', ...) failed", e)

    try:
        lex_block.on_intent("SpeakToAgent", speak_agent_msg)
        report.success("on_intent('SpeakToAgent', ...) added intent condition")
    except Exception as e:
        report.error("on_intent('SpeakToAgent', ...) failed", e)

    # Verify intent conditions were added correctly
    try:
        conditions = lex_block.transitions.get("Conditions", [])
        intent_names = [c["Condition"]["Operands"][0] for c in conditions]
        report.success(
            f"Lex block has {len(conditions)} intent conditions",
            f"Intents: {intent_names}",
        )
        if len(conditions) != 3:
            report.error(
                f"Expected 3 intent conditions, got {len(conditions)}"
            )
    except Exception as e:
        report.error("Failed to verify intent conditions", e)

    # Lex block default and error handlers
    try:
        # Check if ConnectParticipantWithLexBot has otherwise()
        has_otherwise = hasattr(lex_block, "otherwise")
        if has_otherwise:
            lex_block.otherwise(fallback_msg)
            report.success("Lex block has otherwise() for default routing")
        else:
            report.missing(
                "ConnectParticipantWithLexBot has no otherwise() method",
                "Users must use then() or raw transitions for default routing "
                "when no intent matches.",
            )
            lex_block.then(fallback_msg)
            report.success("Used then() as fallback for unmatched intents")
    except Exception as e:
        report.error("Default routing setup failed", e)

    try:
        lex_block.on_error("InputTimeLimitExceeded", timeout_msg)
        lex_block.on_error("NoMatchingCondition", fallback_msg)
        lex_block.on_error("NoMatchingError", error_msg)
        errors = lex_block.transitions.get("Errors", [])
        report.success(
            f"on_error() added {len(errors)} error handlers to lex block",
            f"Types: {[e['ErrorType'] for e in errors]}",
        )
    except Exception as e:
        report.error("Lex block error handler setup failed", e)

    # Terminal wiring
    try:
        order_status_msg.then(disconnect_order)
        return_item_msg.then(disconnect_return)
        speak_agent_msg.then(disconnect_agent)
        fallback_msg.then(disconnect_fallback)
        timeout_msg.then(disconnect_timeout)
        error_msg.then(disconnect_error)
        report.success("Wired all intent handler messages to disconnect blocks")
    except Exception as e:
        report.error("Terminal wiring failed", e)
        return report

    # ----------------------------------------------------------------
    # Phase 5: Friction analysis
    # ----------------------------------------------------------------
    report.friction(
        "LexV2Bot import path discovery requires reading source or docs",
        "A new user might try 'from cxblueprint import LexV2Bot' (which works) "
        "or 'from cxblueprint.blocks import LexV2Bot'. The types module location "
        "(cxblueprint.blocks.types) is not intuitive.",
    )
    report.friction(
        "on_intent() requires exact AWS intent name strings",
        "There is no validation that the intent name matches what is configured "
        "in the Lex bot. Typos (e.g., 'orderStatus' vs 'OrderStatus') will "
        "silently fail at runtime.",
    )
    report.friction(
        "Lex bot prompt text is passed as a constructor parameter, not chained",
        "Unlike some IVR DSLs where you might chain .with_prompt('text'), "
        "the prompt text goes into the lex_bot() call. This is consistent with "
        "get_input() but may surprise users who expect prompt and bot config "
        "to be separate steps.",
    )

    # ----------------------------------------------------------------
    # Phase 6: Block count and validation
    # ----------------------------------------------------------------
    report.block_count = len(flow.blocks)
    report.success(
        f"Flow contains {report.block_count} blocks",
        f"Block types: {dict(flow._block_stats)}",
    )

    try:
        flow.validate()
        report.validation_passed = True
        report.success("flow.validate() passed with no issues")
    except Exception as e:
        report.error("flow.validate() raised an error", e)

    # ----------------------------------------------------------------
    # Phase 7: Compilation
    # ----------------------------------------------------------------
    output_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "output",
        "test_lex_bot.json",
    )
    try:
        flow.compile_to_file(output_path)
        report.compiled = True
        report.success(
            "compile_to_file() succeeded",
            f"Output: {output_path}",
        )
    except Exception as e:
        report.error("compile_to_file() failed", e)

    # Verify output JSON
    if report.compiled:
        try:
            with open(output_path, "r") as f:
                compiled_json = json.load(f)
            actions = compiled_json.get("Actions", [])
            action_types = [a.get("Type") for a in actions]
            report.success(
                f"Output JSON valid: {len(actions)} actions",
                f"Action types: {action_types}",
            )

            # Verify Lex block is present and has intent conditions
            if "ConnectParticipantWithLexBot" in action_types:
                report.success("ConnectParticipantWithLexBot block present in compiled output")
                for action in actions:
                    if action.get("Type") == "ConnectParticipantWithLexBot":
                        params = action.get("Parameters", {})
                        if "LexV2Bot" in params:
                            report.success(
                                "LexV2Bot configuration present in parameters",
                                f"AliasArn: {params['LexV2Bot'].get('AliasArn', 'MISSING')[:40]}...",
                            )
                        else:
                            report.error("LexV2Bot configuration MISSING from parameters")
                        conds = action.get("Transitions", {}).get("Conditions", [])
                        if len(conds) == 3:
                            intents = [c["Condition"]["Operands"][0] for c in conds]
                            report.success(
                                f"Lex block has {len(conds)} intent conditions in compiled output",
                                f"Intents: {intents}",
                            )
                        else:
                            report.error(
                                f"Lex block has {len(conds)} conditions (expected 3)"
                            )
                        break
            else:
                report.error("ConnectParticipantWithLexBot block MISSING from compiled output")
        except Exception as e:
            report.error("Output JSON verification failed", e)

    return report


if __name__ == "__main__":
    from qa_helpers import print_report
    print_report(run_test())
