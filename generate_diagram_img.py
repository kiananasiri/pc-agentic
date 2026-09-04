import matplotlib.pyplot as plt
import matplotlib.patches as patches

def draw_backend_diagram():
    fig, ax = plt.subplots(figsize=(14, 11), dpi=300)
    ax.set_facecolor('#0f172a') # Dark slate theme matching modern dashboard visuals
    fig.patch.set_facecolor('#0f172a')
    
    # Hide axes
    ax.axis('off')
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)

    # Title
    ax.text(50, 96, "معماری لایه بک‌اند و ایجنت‌های سیستم (Backend & Agent Architecture)", 
            color="#ffffff", fontsize=16, fontweight='bold', ha='center', va='center', fontfamily='sans-serif')

    # Helper function to draw rounded box
    def draw_box(x, y, w, h, title, subtitle="", color="#1e293b", border="#38bdf8", text_color="#ffffff"):
        box = patches.FancyBboxPatch((x - w/2, y - h/2), w, h,
                                 boxstyle="round,pad=0.5,rounding_size=1.5",
                                 ec=border, fc=color, lw=1.8, zorder=3)
        ax.add_patch(box)
        if subtitle:
            ax.text(x, y + h*0.18, title, color=text_color, fontsize=10, fontweight='bold', ha='center', va='center')
            ax.text(x, y - h*0.20, subtitle, color="#cbd5e1", fontsize=8, ha='center', va='center')
        else:
            ax.text(x, y, title, color=text_color, fontsize=10, fontweight='bold', ha='center', va='center')

    # Helper function for arrow
    def draw_arrow(x1, y1, x2, y2, color="#94a3b8", label=""):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="->", color=color, lw=1.5, mutation_scale=12), zorder=2)
        if label:
            mx, my = (x1 + x2)/2, (y1 + y2)/2
            ax.text(mx, my, label, color="#94a3b8", fontsize=7.5, ha='center', va='center',
                    bbox=dict(boxstyle="round,pad=0.2", fc="#0f172a", ec="none", alpha=0.8))

    # Layer 1: Request Payload
    draw_box(50, 89, 32, 5, "Request Payload", "Question + Model Config", color="#1e293b", border="#64748b")
    
    # Layer 2: Orchestrator
    draw_box(50, 78, 36, 6, "Agno Orchestrator", "run_agno_chat() & Intent Router", color="#312e81", border="#818cf8")
    draw_arrow(50, 86.5, 50, 81, "#818cf8")

    # Layer 3: Data Services
    draw_box(28, 66, 24, 5.5, "Binance API", "Live OHLCV Candles", color="#064e3b", border="#34d399")
    draw_box(72, 66, 24, 5.5, "CoinGecko API", "On-Chain & Smart Money", color="#064e3b", border="#34d399")
    
    draw_arrow(42, 75, 28, 68.75, "#34d399", "TA Query")
    draw_arrow(58, 75, 72, 68.75, "#34d399", "FA Query")

    # Layer 4: Agents (5 Agents spread horizontally)
    agent_y = 51
    agent_w, agent_h = 17, 7
    
    draw_box(10, agent_y, agent_w, agent_h, "Technical Agent", "Chart & Candle Analysis", color="#831843", border="#f472b6")
    draw_box(30, agent_y, agent_w, agent_h, "Fundamental Agent", "Smart Money & Netflow", color="#831843", border="#f472b6")
    draw_box(50, agent_y, agent_w, agent_h, "Code Agent", "Pandas & Python Analysis", color="#831843", border="#f472b6")
    draw_box(70, agent_y, agent_w, agent_h, "Combined TA/FA", "Integrated Market Analysis", color="#831843", border="#f472b6")
    draw_box(90, agent_y, agent_w, agent_h, "Reactive Agent", "DuckDuckGo Web Search", color="#831843", border="#f472b6")

    # Data to Agent Arrows
    draw_arrow(28, 63.25, 10, 54.5, "#f472b6")
    draw_arrow(72, 63.25, 30, 54.5, "#f472b6")
    draw_arrow(50, 75, 50, 54.5, "#f472b6", "code=True")
    draw_arrow(28, 63.25, 70, 54.5, "#f472b6")
    draw_arrow(72, 63.25, 70, 54.5, "#f472b6")
    draw_arrow(50, 75, 90, 54.5, "#f472b6", "General")

    # Layer 5: ToolKits
    tool_y = 35
    tool_w, tool_h = 17, 7.5

    draw_box(10, tool_y, tool_w, tool_h, "TAToolKit", "get_chart_summary()\nget_indicator_data()", color="#1e3a8a", border="#60a5fa")
    draw_box(30, tool_y, tool_w, tool_h, "FundamentalToolKit", "get_fundamental_summary()\nget_metric_data()", color="#1e3a8a", border="#60a5fa")
    draw_box(50, tool_y, tool_w, tool_h, "CodeTools", "Python REPL / Pandas\nDynamic Calculation", color="#1e3a8a", border="#60a5fa")
    draw_box(70, tool_y, tool_w, tool_h, "Combined ToolKits", "TAToolKit +\nFundamentalToolKit", color="#1e3a8a", border="#60a5fa")
    draw_box(90, tool_y, tool_w, tool_h, "WebTools", "DuckDuckGo Search\nReal-time News API", color="#1e3a8a", border="#60a5fa")

    # Agent to Tool Arrows
    for x in [10, 30, 50, 70, 90]:
        draw_arrow(x, 47.5, x, 38.75, "#60a5fa")

    # Layer 6: LLM & Pricing Engine
    draw_box(50, 20, 48, 6, "OpenAI API Endpoint", "/v1/chat/completions (gpt-4o / o3-mini)", color="#581c87", border="#c084fc")
    for x in [10, 30, 50, 70, 90]:
        draw_arrow(x, 31.25, 50, 23, "#c084fc")

    draw_box(50, 10, 52, 5.5, "Token & Pricing Engine", "Cost Calculation ($) + Thinking Process Extraction", color="#312e81", border="#a5b4fc")
    draw_arrow(50, 17, 50, 12.75, "#a5b4fc")

    # Layer 7: Response Payload
    draw_box(50, 2, 40, 4.5, "Response Payload", "Answer + Price ($) + Reasoning Steps", color="#1e293b", border="#64748b")
    draw_arrow(50, 7.25, 50, 4.25, "#64748b")

    plt.tight_layout()
    plt.savefig('backend_architecture_diagram.png', bbox_inches='tight', facecolor='#0f172a', dpi=300)
    plt.close()
    print("Diagram generated successfully as backend_architecture_diagram.png!")

if __name__ == '__main__':
    draw_backend_diagram()
