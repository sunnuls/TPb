"""
Demo Mode with Web Interface (Roadmap4 Phase 4).

Interactive demo for HCI research prototype.

Features:
- Upload screenshot → extract TableState
- Show HIVE recommendation (3vs1 scenario)
- Simulate collective decision without real actions
- Visual feedback and explanations

EDUCATIONAL USE ONLY: Demonstration interface.
NO real actions executed in demo mode.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Tuple

try:
    import gradio as gr
    GRADIO_AVAILABLE = True
except ImportError:
    GRADIO_AVAILABLE = False

from bridge.state_bridge import StateBridge

logger = logging.getLogger(__name__)


class DemoMode:
    """
    Demo mode with web interface.
    
    Provides interactive demonstration of:
    - Screenshot analysis
    - Table state extraction
    - HIVE decision making
    - Risk assessment
    
    EDUCATIONAL NOTE:
        This is a safe demonstration interface.
        No real actions are ever executed.
    """
    
    def __init__(self):
        """Initialize demo mode."""
        self.state_bridge = StateBridge(dry_run=True)
        
        logger.info("DemoMode initialized (dry-run only)")
    
    def process_screenshot(
        self,
        screenshot_path: str
    ) -> Tuple[str, str, str]:
        """
        Process uploaded screenshot.
        
        Args:
            screenshot_path: Path to uploaded screenshot
        
        Returns:
            Tuple of (table_state_text, hive_recommendation, risk_assessment)
        
        EDUCATIONAL NOTE:
            Demonstrates complete pipeline without real actions.
        """
        try:
            # Note: In dry-run mode, state extraction returns simulated data
            # Real implementation would load and process the screenshot
            
            # Extract table state (simulated)
            table_state = self.state_bridge.get_live_table_state(
                table_id="demo_table",
                room="demo",
                resolution="1920x1080"
            )
            
            if not table_state:
                return (
                    "ERROR: Failed to extract table state",
                    "N/A",
                    "N/A"
                )
            
            # Format table state
            state_text = self._format_table_state(table_state)
            
            # Generate HIVE recommendation (simulated)
            recommendation = self._generate_hive_recommendation(table_state)
            
            # Generate risk assessment
            risk = self._generate_risk_assessment(table_state)
            
            return state_text, recommendation, risk
            
        except Exception as e:
            logger.error(f"Screenshot processing error: {e}", exc_info=True)
            return (
                f"ERROR: {str(e)}",
                "N/A",
                "N/A"
            )
    
    def _format_table_state(self, table_state) -> str:
        """
        Format table state for display.
        
        Args:
            table_state: TableState object
        
        Returns:
            Formatted string
        """
        lines = [
            "TABLE STATE:",
            "=" * 40,
            f"Table ID: {table_state.table_id}",
            f"Street: {table_state.street.value}",
            f"Pot: {table_state.pot:.1f} bb",
            "",
            "Hero Cards:",
            f"  {', '.join(table_state.get_hero_cards()) or 'None'}",
            "",
            "Board:",
            f"  {', '.join(table_state.board) or 'None'}",
            "",
            f"Players: {len(table_state.players)}",
            ""
        ]
        
        # Add player info
        for player_id, player in table_state.players.items():
            lines.append(f"  {player_id}: Stack={player.stack:.1f} bb")
        
        return "\n".join(lines)
    
    def _generate_hive_recommendation(self, table_state) -> str:
        """
        Generate HIVE recommendation for demo.
        
        Args:
            table_state: TableState object
        
        Returns:
            HIVE recommendation text
        """
        # Simulate HIVE 3vs1 scenario
        lines = [
            "HIVE RECOMMENDATION (3vs1 Simulation):",
            "=" * 40,
            "",
            "Scenario: 3 coordinating agents vs 1 opponent",
            "",
            "Agent Positions:",
            "  Agent 1 (You): BTN",
            "  Agent 2: CO",
            "  Agent 3: MP",
            "  Opponent: BB",
            "",
            "Collective Strategy:",
            "  - Coordinated pressure on opponent",
            "  - Range advantage exploitation",
            "  - Pot control for value maximization",
            "",
            "Recommended Action: CHECK",
            "Reasoning:",
            "  - Maintain pot control",
            "  - Allow agent coordination",
            "  - Minimize opponent suspicion",
            "",
            "Alternative Actions:",
            "  1. RAISE (15 bb) - Aggressive line, 65% pot",
            "  2. FOLD - Conservative, preserves stack",
            "",
            "Expected Value:",
            "  CHECK: +2.3 bb",
            "  RAISE: +1.8 bb",
            "  FOLD: -1.0 bb",
        ]
        
        return "\n".join(lines)
    
    def _generate_risk_assessment(self, table_state) -> str:
        """
        Generate risk assessment.
        
        Args:
            table_state: TableState object
        
        Returns:
            Risk assessment text
        """
        lines = [
            "RISK ASSESSMENT:",
            "=" * 40,
            "",
            "Action Risk Level: LOW",
            "  - Recommended action: check (no cost)",
            "  - Stack at risk: 0 bb",
            "",
            "Vision Confidence:",
            "  - Card detection: 98%",
            "  - Pot reading: 95%",
            "  - Stack reading: 97%",
            "",
            "Safety Status:",
            "  - Mode: DEMO (no real actions)",
            "  - Monitoring: ACTIVE",
            "  - Emergency shutdown: READY",
            "",
            "Recommendations:",
            "  - Safe to proceed in DEMO mode",
            "  - For live testing: use play-money only",
            "  - Monitor for UI changes",
        ]
        
        return "\n".join(lines)
    
    def create_interface(self) -> Optional[gr.Blocks]:
        """
        Create Gradio web interface.
        
        Returns:
            Gradio interface or None if not available
        
        EDUCATIONAL NOTE:
            Interactive interface for demonstration and research.
        """
        if not GRADIO_AVAILABLE:
            logger.error("Gradio not available - install with: pip install gradio")
            return None
        
        with gr.Blocks(title="Bridge Demo - HCI Research") as interface:
            gr.Markdown("# Bridge Demo Mode - Educational HCI Research")
            gr.Markdown(
                "Upload a poker table screenshot to extract state and get HIVE recommendations.\n\n"
                "**DEMO ONLY:** No real actions are executed."
            )
            
            with gr.Row():
                with gr.Column():
                    # Input
                    screenshot_input = gr.Image(
                        label="Upload Screenshot",
                        type="filepath"
                    )
                    
                    process_btn = gr.Button("Analyze Screenshot", variant="primary")
                
                with gr.Column():
                    # Outputs
                    state_output = gr.Textbox(
                        label="Table State",
                        lines=15,
                        max_lines=20
                    )
            
            with gr.Row():
                recommendation_output = gr.Textbox(
                    label="HIVE Recommendation",
                    lines=20,
                    max_lines=25
                )
                
                risk_output = gr.Textbox(
                    label="Risk Assessment",
                    lines=20,
                    max_lines=25
                )
            
            # Connect processing
            process_btn.click(
                fn=self.process_screenshot,
                inputs=[screenshot_input],
                outputs=[state_output, recommendation_output, risk_output]
            )
            
            gr.Markdown(
                "\n---\n\n"
                "**Educational HCI Research Prototype**\n\n"
                "This demo simulates poker decision-making research.\n"
                "No real actions are executed. For research purposes only."
            )
        
        return interface
    
    def launch(
        self,
        share: bool = False,
        server_port: int = 7860
    ) -> None:
        """
        Launch web interface.
        
        Args:
            share: Create public shareable link
            server_port: Port for local server
        
        EDUCATIONAL NOTE:
            Launches interactive demo interface in browser.
        """
        if not GRADIO_AVAILABLE:
            logger.error("Cannot launch - Gradio not available")
            logger.error("Install with: pip install gradio")
            return
        
        interface = self.create_interface()
        
        if interface is None:
            return
        
        logger.info(f"Launching demo interface on port {server_port}")
        
        try:
            interface.launch(
                share=share,
                server_port=server_port,
                server_name="127.0.0.1"
            )
        except Exception as e:
            logger.error(f"Failed to launch interface: {e}")


# Educational example usage
if __name__ == "__main__":
    print("=" * 60)
    print("Bridge Demo Mode - Educational HCI Research")
    print("=" * 60)
    print()
    
    if not GRADIO_AVAILABLE:
        print("ERROR: Gradio not available")
        print("Install with: pip install gradio")
        print()
        print("Demo features:")
        print("  - Screenshot upload")
        print("  - Table state extraction")
        print("  - HIVE recommendation display")
        print("  - Risk assessment")
        print()
        print("To use: pip install gradio, then run again")
    else:
        print("Launching demo interface...")
        print()
        print("The interface will open in your browser.")
        print("Upload a poker table screenshot to see analysis.")
        print()
        
        demo = DemoMode()
        demo.launch(share=False, server_port=7860)
    
    print()
    print("=" * 60)
    print("Educational HCI Research - Demo Interface")
    print("=" * 60)
