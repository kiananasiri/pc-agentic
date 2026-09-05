from public_app.src.config import get_llm, get_agent, get_llm_name
from llama_index.core.llms import ChatMessage
from llama_index.core.schema import ImageDocument
from llama_index.core.tools import FunctionTool
from llama_index.core import PromptTemplate
from llama_index.core.agent import ReActAgent
from llama_index.core.llms import TextBlock, ImageBlock

from ast import literal_eval
import base64
import tempfile
import os
import requests
import time
import tiktoken
import re
from .prompts import leakage_detection_prompt

temp_files_paths = []


def count_refinement_steps(history):
    """
    Count consecutive query refinement steps from the end of history.

    Args:
        history (list): List of conversation history dictionaries

    Returns:
        int: Number of consecutive query refinements
    """
    for i, entry in enumerate(reversed(history)):
        if not entry.get("query_refinement"):
            return i
    return len(history)


def create_chat_message(role, message, image_docs=None, is_multi_modal=False):
    """Helper function to create chat messages with or without images."""
    if not message:
        message = " "
    try:
        if is_multi_modal and image_docs:
            # Convert base64 image to ImageDocument first
            image_document = base64_to_image_document(image_docs)
            # Create blocks for ChatMessage
            blocks = [TextBlock(text=message)]
            if (
                image_document.image_path
            ):  # Assuming base64_to_image_document stores it as a path
                blocks.append(ImageBlock(path=image_document.image_path))
            elif image_document.image_url:
                blocks.append(ImageBlock(url=image_document.image_url))
            # Potentially handle image_document.image (raw bytes) if needed, though path/URL is more common

            return ChatMessage(role=role, blocks=blocks)
    except Exception as e:
        print(f"Error creating multi-modal chat message: {e}")
        # Fall back to regular chat message if there's an error with multi-modal
    return ChatMessage(role=role, content=message)


def prompt_builder(
    history, new_message, system_prompt, image_documents=None, consider_image=True
):
    """
    Builds a chat history prompt for a chatbot.

    Args:
        history (list[dict]): Chat history with question/answer pairs
        new_message (str): New user message
        system_prompt (str): Initial system prompt
        image_documents (str, optional): Base64 encoded image
        consider_image (bool): Whether to process images. Defaults to True

    Returns:
        list[ChatMessage]: Chat history with system prompt and messages
    """
    if history is None:
        history = []
    chat_history = [ChatMessage(role="system", content=system_prompt)]

    for qa_pair in history:
        chat_history.extend(
            [
                create_chat_message(
                    "user",
                    qa_pair.get("question", " "),
                    qa_pair.get("image_base64", None),
                    consider_image,
                ),
                ChatMessage(role="assistant", content=qa_pair.get("answer", " ")),
            ]
        )

    chat_history.append(
        create_chat_message("user", new_message, image_documents, consider_image)
    )

    return chat_history


def dialogue_builder(history):
    if not history:
        return "This is the first message in the conversation."

    dialogue_history = []
    for i, entry in enumerate(history, start=1):
        dialogue_history.extend(
            [f"{i}. User: {entry['question']}", f"{i}. Assistant: {entry['answer']}"]
        )

    return "\n".join(dialogue_history)


def calculate_price(input_token, output_token, model="gpt-4o-mini"):
    """
    Calculate the price based on the number of input and output tokens and the model used.

    Args:
        input_token (int): The number of input tokens.
        output_token (int): The number of output tokens.
        model (str, optional): The model used for pricing. Default is "gpt-4o-mini".

    Returns:
        float: The total price calculated based on the input and output tokens.
    """
    pricing = {
        "gpt-4o-mini": {
            "input": 0.00015 / 1000,  # $0.15 per million tokens
            "output": 0.0006 / 1000,  # $0.60 per million tokens
        },
        "gpt-4.1": {
            "input": 0.002 / 1000,  # $2 per million tokens
            "output": 0.008 / 1000,  # $8 per million tokens
        },
        "gpt-4.1-mini": {
            "input": 0.0004 / 1000,  # $0.40 per million tokens
            "output": 0.0016 / 1000,  # $1.60 per million tokens
        },
        "gpt-4.1-nano": {
            "input": 0.0001 / 1000,  # $0.10 per million tokens
            "output": 0.0004 / 1000,  # $0.40 per million tokens
        },
        "gpt-4o": {
            "input": 0.0025 / 1000,  # $2.50 per million tokens
            "output": 0.010 / 1000,  # $10 per million tokens
        },
        "gpt-4.5-preview": {
            "input": 0.075 / 1000,  # $75 per million tokens
            "output": 0.150 / 1000,  # $150 per million tokens
        },
        "o3-mini": {
            "input": 0.0011 / 1000,  # $1.10 per million tokens
            "output": 0.0044 / 1000,  # $4.40 per million tokens
        },
        "o1": {
            "input": 0.015 / 1000,  # $15 per million tokens
            "output": 0.060 / 1000,  # $60 per million tokens
        },
        "gpt-5-mini": {
            "input": 0.00025 / 1000,  # $0.25 per million tokens
            "output": 0.002 / 1000,  # $2 per million tokens
        },
        "gpt-5-nano": {
            "input": 0.00005 / 1000,  # $0.05 per million tokens
            "output": 0.0004 / 1000,  # $0.40 per million tokens
        },
        "gpt-5": {
            "input": 0.00125 / 1000,  # $1.25 per million tokens
            "output": 0.010 / 1000,  # $10 per million tokens
        }
    }

    input_price = pricing[model]["input"] * input_token
    output_price = pricing[model]["output"] * output_token
    total_price = input_price + output_price

    return total_price


def calculate_long_position_reward_ratio(
    entry_price: float, stop_loss: float, take_profit: list
) -> dict:
    """
    Calculate the Risk-Reward Ratio (RR) for a long trading setup.

    The Risk-Reward Ratio is calculated as: Reward / Risk
    - For long positions: Risk = Entry Price - Stop Loss, Reward = Take Profit - Entry Price

    Examples:
    1. Long Position:
       Entry Price: 100, Stop Loss: 95, Take Profit: 115
       Risk = 100 - 95 = 5
       Reward = 115 - 100 = 15
       RR = 15 / 5 = 3 (For every 1 unit of risk, potential reward is 3 units)

    Parameters:
        entry_price (float): The entry price (EP).
        stop_loss (float): The stop-loss price (SL).
        take_profit (list of float): List of take-profit prices (TP1, TP2, TP3, etc.).

    Returns:
        dict: A dictionary containing the Risk-Reward Ratios (RR) for each take-profit level.
              Format: {'TP1': RR1, 'TP2': RR2, 'TP3': RR3, ...}
    """
    rr_ratios = {}

    # Calculate risk for long position
    risk = entry_price - stop_loss

    # Ensure risk is positive
    if risk <= 0:
        raise ValueError(
            "Invalid risk calculation. Stop loss must be below entry price for long positions."
        )

    # Calculate reward ratio for each take profit level
    for i, tp in enumerate(take_profit, start=1):
        reward = tp - entry_price

        # Ensure reward is positive
        if reward <= 0:
            raise ValueError(
                f"Invalid reward calculation for TP{i}. Take profit must be above entry price for long positions."
            )

        rr_ratios[f"TP{i}"] = reward / risk

    return rr_ratios


def calculate_short_position_reward_ratio(
    entry_price: float, stop_loss: float, take_profit: list
) -> dict:
    """
    Calculate the Risk-Reward Ratio (RR) for a short trading setup.

    The Risk-Reward Ratio is calculated as: Reward / Risk
    - For short positions: Risk = Stop Loss - Entry Price, Reward = Entry Price - Take Profit

    Examples:
    1. Short Position:
       Entry Price: 200, Stop Loss: 210, Take Profit: 180
       Risk = 210 - 200 = 10
       Reward = 200 - 180 = 20
       RR = 20 / 10 = 2 (For every 1 unit of risk, potential reward is 2 units)

    Parameters:
        entry_price (float): The entry price (EP).
        stop_loss (float): The stop-loss price (SL).
        take_profit (list of float): List of take-profit prices (TP1, TP2, TP3, etc.).

    Returns:
        dict: A dictionary containing the Risk-Reward Ratios (RR) for each take-profit level.
              Format: {'TP1': RR1, 'TP2': RR2, 'TP3': RR3, ...}
    """
    rr_ratios = {}

    # Calculate risk for short position
    risk = stop_loss - entry_price

    # Ensure risk is positive
    if risk <= 0:
        raise ValueError(
            "Invalid risk calculation. Stop loss must be above entry price for short positions."
        )

    # Calculate reward ratio for each take profit level
    for i, tp in enumerate(take_profit, start=1):
        reward = entry_price - tp

        # Ensure reward is positive
        if reward <= 0:
            raise ValueError(
                f"Invalid reward calculation for TP{i}. Take profit must be below entry price for short positions."
            )

        rr_ratios[f"TP{i}"] = reward / risk

    return rr_ratios


def calculate_leverage_ratio(risk_percentage):
    """
    Calculate the maximum leverage based on the given risk percentage.
    
    Formula: LV = 90 ÷ % SL, then rounded down to the nearest integer.
    
    Example:
    If stop loss percentage is 2.01%:
    LV = 90 ÷ 2.01 = 44.77
    Rounded down: 44X leverage

    Parameters:
    risk_percentage (float): The risk percentage (e.g., 2.01 for 2.01%).

    Returns:
    int: The calculated leverage rounded down to the nearest integer.
    """
    if risk_percentage <= 0:
        raise ValueError("Risk percentage must be greater than 0.")
    
    if risk_percentage > 90:
        raise ValueError("Risk percentage cannot be greater than 90%.")

    leverage = 90 / risk_percentage
    # Round down to the nearest integer
    return int(leverage)


def calculate_leverage_from_prices(entry_price, stop_loss):
    """
    Calculate leverage ratio from entry and stop loss prices.
    
    Parameters:
    entry_price (float): Entry price
    stop_loss (float): Stop loss price
    
    Returns:
    int: Calculated leverage ratio
    """
    if entry_price <= 0 or stop_loss <= 0:
        raise ValueError("Prices must be greater than 0.")
    
    # Calculate risk percentage
    if entry_price > stop_loss:  # Long position
        risk_percentage = ((entry_price - stop_loss) / entry_price) * 100
    else:  # Short position
        risk_percentage = ((stop_loss - entry_price) / entry_price) * 100
    
    return calculate_leverage_ratio(risk_percentage)


def validate_trading_calculations(entry_price, stop_loss, take_profits, position_type="long", resolution=None):
    """
    Validate trading calculations and return detailed results.
    
    Parameters:
    entry_price (float): Entry price
    stop_loss (float): Stop loss price
    take_profits (list): List of take profit prices
    position_type (str): "long" or "short"
    
    Returns:
    dict: Validation results with calculations and recommendations
    """
    results = {
        "is_valid": True,
        "errors": [],
        "warnings": [],
        "calculations": {}
    }
    
    # Validate inputs
    if entry_price <= 0 or stop_loss <= 0:
        results["is_valid"] = False
        results["errors"].append("Entry price and stop loss must be greater than 0")
        return results
    
    for tp in take_profits:
        if tp <= 0:
            results["is_valid"] = False
            results["errors"].append("Take profit prices must be greater than 0")
            return results
    
    # Pre-validation: Ensure price order matches position type
    if position_type.lower() == "long":
        if not all(tp > entry_price for tp in take_profits):
            results["is_valid"] = False
            results["errors"].append("For long positions, all take profits must be above entry price.")
            return results
        if not entry_price > stop_loss:
            results["is_valid"] = False
            results["errors"].append("For long positions, entry price must be above stop loss.")
            return results
    else:  # short
        if not all(tp < entry_price for tp in take_profits):
            results["is_valid"] = False
            results["errors"].append("For short positions, all take profits must be below entry price.")
            return results
        if not entry_price < stop_loss:
            results["is_valid"] = False
            results["errors"].append("For short positions, entry price must be below stop loss.")
            return results
    
    # Calculate risk percentage
    if position_type.lower() == "long":
        if entry_price <= stop_loss:
            results["is_valid"] = False
            results["errors"].append("For long positions, stop loss must be below entry price")
            return results
        risk_percentage = ((entry_price - stop_loss) / entry_price) * 100
    else:  # short
        if entry_price >= stop_loss:
            results["is_valid"] = False
            results["errors"].append("For short positions, stop loss must be above entry price")
            return results
        risk_percentage = ((stop_loss - entry_price) / entry_price) * 100
    
    # Calculate leverage
    try:
        leverage = calculate_leverage_ratio(risk_percentage)
        results["calculations"]["leverage"] = leverage
        results["calculations"]["risk_percentage"] = risk_percentage
    except ValueError as e:
        results["is_valid"] = False
        results["errors"].append(f"Leverage calculation error: {str(e)}")
        return results
    
    # Calculate risk-reward ratios
    try:
        if position_type.lower() == "long":
            rr_ratios = calculate_long_position_reward_ratio(entry_price, stop_loss, take_profits)
        else:
            rr_ratios = calculate_short_position_reward_ratio(entry_price, stop_loss, take_profits)
        
        results["calculations"]["risk_reward_ratios"] = rr_ratios
        
        # Validate RR ratios
        for tp_name, ratio in rr_ratios.items():
            if ratio < 0.5:
                results["errors"].append(f"{tp_name} RR ratio too low: {ratio:.2f} (fees exceed profit)")
            elif ratio < 1.0:
                results["warnings"].append(f"{tp_name} RR ratio too low: {ratio:.2f}")
            elif ratio > 10.0:
                results["warnings"].append(f"{tp_name} RR ratio too high: {ratio:.2f}")
                
    except ValueError as e:
        results["is_valid"] = False
        results["errors"].append(f"Risk-reward calculation error: {str(e)}")
        return results
    
    # Validate risk percentage by timeframe
    if risk_percentage < 0.5:
        results["warnings"].append("Risk percentage very low (< 0.5%) - may be too tight")
    elif risk_percentage < 2.0 and resolution == "15m":
        results["warnings"].append("Risk percentage too low for 15m timeframe (< 2.0%) - fees may exceed profit")
    elif risk_percentage > 20:
        results["warnings"].append("Risk percentage very high (> 20%) - may be too wide")
    
    # Validate leverage
    if leverage < 1:
        results["warnings"].append("Leverage too low (< 1X)")
    elif leverage > 100:
        results["warnings"].append("Leverage too high (> 100X)")
    
    return results


def calculate_comprehensive_trading_parameters(entry_price, stop_loss, take_profits, position_type="long", resolution=None):
    """
    Calculate comprehensive trading parameters with validation.
    
    Parameters:
    entry_price (float): Entry price
    stop_loss (float): Stop loss price
    take_profits (list): List of take profit prices
    position_type (str): "long" or "short"
    
    Returns:
    dict: Complete trading parameters with validation
    """
    validation = validate_trading_calculations(entry_price, stop_loss, take_profits, position_type, resolution)
    
    if not validation["is_valid"]:
        return {
            "success": False,
            "errors": validation["errors"],
            "warnings": validation["warnings"]
        }
    
    # Calculate additional parameters
    risk_amount = abs(entry_price - stop_loss)
    total_reward = 0
    for tp in take_profits:
        if position_type.lower() == "long":
            reward = tp - entry_price
        else:
            reward = entry_price - tp
        total_reward += reward
    
    return {
        "success": True,
        "entry_price": entry_price,
        "stop_loss": stop_loss,
        "take_profits": take_profits,
        "position_type": position_type,
        "risk_amount": risk_amount,
        "total_reward": total_reward,
        "leverage": validation["calculations"]["leverage"],
        "risk_percentage": validation["calculations"]["risk_percentage"],
        "risk_reward_ratios": validation["calculations"]["risk_reward_ratios"],
        "warnings": validation["warnings"],
        "recommendations": [
            "Use exact price values, not ranges",
            "Ensure stop loss is appropriate for timeframe",
            "Verify risk-reward ratios are realistic",
            "Check leverage is within safe limits"
        ]
    }


calculate_leverage_ratio_tool = FunctionTool.from_defaults(
    fn=calculate_leverage_ratio,
    name="calculate_leverage_ratio",
    description="""Calculates the Leverage Ratio (LR) for a trade based on the risk percentage. The Leverage Ratio is determined by the formula: LR = 90 / Risk Percentage, rounded down to the nearest integer. This tool ensures that the recommended leverage aligns with the trader's risk tolerance and trading strategy. The output is a clear Leverage Ratio value that can be used to manage risk effectively in trading.""",
)

calculate_leverage_from_prices_tool = FunctionTool.from_defaults(
    fn=calculate_leverage_from_prices,
    name="calculate_leverage_from_prices",
    description="""Calculates the Leverage Ratio (LR) directly from entry and stop loss prices. This tool automatically determines if it's a long or short position and calculates the appropriate leverage ratio using the formula: LR = 90 / Risk Percentage. Use this tool when you have entry and stop loss prices and need to calculate the recommended leverage.""",
)


calculate_long_position_reward_ratio_tool = FunctionTool.from_defaults(
    fn=calculate_long_position_reward_ratio,
    name="calculate_long_position_reward_ratio",
    description="""Calculates the Risk-Reward (RR) ratio for LONG (buy) trading positions to help evaluate trade profitability and risk management.

This tool computes the ratio between potential reward and risk specifically for long trading positions where you buy low and sell high. The Risk-Reward ratio is a crucial metric that helps traders assess whether a long trade setup offers favorable odds before entering a position.

The Risk-Reward Ratio is calculated as: Reward / Risk
- For long positions: Risk = Entry Price - Stop Loss, Reward = Take Profit - Entry Price

Example:
Long Position:
Entry Price: 100, Stop Loss: 95, Take Profit: 115
Risk = 100 - 95 = 5
Reward = 115 - 100 = 15
RR = 15 / 5 = 3 (For every 1 unit of risk, potential reward is 3 units)

The function returns a dictionary containing the Risk-Reward Ratios for each take-profit level in the format: {'TP1': RR1, 'TP2': RR2, 'TP3': RR3, ...}

A higher RR ratio indicates better risk-adjusted potential returns. Generally, traders prefer RR ratios of 2:1 or higher for favorable risk management.""",
)

calculate_short_position_reward_ratio_tool = FunctionTool.from_defaults(
    fn=calculate_short_position_reward_ratio,
    name="calculate_short_position_reward_ratio",
    description="""Calculates the Risk-Reward (RR) ratio for SHORT (sell) trading positions to help evaluate trade profitability and risk management.

This tool computes the ratio between potential reward and risk specifically for short trading positions where you sell high and buy low. The Risk-Reward ratio is a crucial metric that helps traders assess whether a short trade setup offers favorable odds before entering a position.

The Risk-Reward Ratio is calculated as: Reward / Risk
- For short positions: Risk = Stop Loss - Entry Price, Reward = Entry Price - Take Profit

Example:
Short Position:
Entry Price: 200, Stop Loss: 210, Take Profit: 180
Risk = 210 - 200 = 10
Reward = 200 - 180 = 20
RR = 20 / 10 = 2 (For every 1 unit of risk, potential reward is 2 units)

The function returns a dictionary containing the Risk-Reward Ratios for each take-profit level in the format: {'TP1': RR1, 'TP2': RR2, 'TP3': RR3, ...}

A higher RR ratio indicates better risk-adjusted potential returns. Generally, traders prefer RR ratios of 2:1 or higher for favorable risk management.""",
)

calculate_comprehensive_trading_parameters_tool = FunctionTool.from_defaults(
    fn=calculate_comprehensive_trading_parameters,
    name="calculate_comprehensive_trading_parameters",
    description="""Calculates comprehensive trading parameters including leverage, risk-reward ratios, and validation for both long and short positions.

This tool provides a complete analysis of trading parameters with built-in validation to ensure realistic and safe trading setups.

Parameters:
- entry_price (float): The exact entry price
- stop_loss (float): The exact stop loss price  
- take_profits (list): List of exact take profit prices
- position_type (str): "long" or "short"
- resolution (str): Timeframe resolution (e.g., "15m", "1h", "4h") for validation

Returns:
- Complete trading parameters with validation
- Leverage ratio calculated using LR = 90 / Risk Percentage
- Risk-reward ratios for each take profit level
- Warnings and recommendations for parameter optimization
- Timeframe-specific validation (e.g., 15m minimum 2.0% SL)

Example:
Long Position: entry_price=100, stop_loss=95, take_profits=[110, 115], position_type="long", resolution="15m"
Short Position: entry_price=200, stop_loss=210, take_profits=[190, 180], position_type="short", resolution="1h"

The tool validates all calculations and provides warnings for unrealistic parameters.""",
)

validate_trading_calculations_tool = FunctionTool.from_defaults(
    fn=validate_trading_calculations,
    name="validate_trading_calculations", 
    description="""Validates trading calculations and provides detailed feedback on parameter quality.

This tool checks if trading parameters are realistic and provides specific warnings and recommendations.

Parameters:
- entry_price (float): The exact entry price
- stop_loss (float): The exact stop loss price
- take_profits (list): List of exact take profit prices  
- position_type (str): "long" or "short"
- resolution (str): Timeframe resolution (e.g., "15m", "1h", "4h") for validation

Returns:
- Validation results with detailed feedback
- Calculation errors if any
- Warnings for suboptimal parameters
- Recommendations for improvement
- Timeframe-specific validation (e.g., 15m minimum 2.0% SL)

The tool ensures all calculations follow the correct formulas:
- Leverage = 90 / Risk Percentage
- Risk-Reward = Reward / Risk
- For long: Risk = Entry - Stop Loss, Reward = Take Profit - Entry
- For short: Risk = Stop Loss - Entry, Reward = Entry - Take Profit""",
)


def count_tokens(text):
    encoding = tiktoken.encoding_for_model(get_llm_name())
    return len(encoding.encode(text))


def invoke_ReAct(system_prompt, plan):
    agent_ReAct = ReActAgent.from_tools(
        [
            calculate_long_position_reward_ratio_tool, 
            calculate_short_position_reward_ratio_tool, 
            calculate_leverage_ratio_tool,
            calculate_leverage_from_prices_tool,
            calculate_comprehensive_trading_parameters_tool,
            validate_trading_calculations_tool,
        ], 
        llm=get_llm(),
    )
    system_prompt += """

**CRITICAL CALCULATION REQUIREMENTS:**

1. **ALWAYS use the provided calculation tools** for accurate RR and LR computations
2. **NEVER calculate manually** - use the tools to ensure accuracy
3. **Validate all parameters** using the validation tools
4. **Provide exact price values** - never use ranges or approximations
5. **Follow the correct formulas:**
   - Leverage = 90 / Risk Percentage (rounded down)
   - Risk-Reward = Reward / Risk
   - For long positions: Risk = Entry - Stop Loss, Reward = Take Profit - Entry
   - For short positions: Risk = Stop Loss - Entry, Reward = Entry - Take Profit

**MANDATORY STEPS:**
1. Extract exact price values from the analysis
2. Use calculate_comprehensive_trading_parameters_tool for complete analysis
3. Use validate_trading_calculations_tool to verify results
4. Present results in a clear tabular format with exact values
"""
    agent_system_prompt = PromptTemplate(system_prompt)
    agent_ReAct.update_prompts({"agent_worker:system_prompt": agent_system_prompt})
    agent_ReAct.reset()
    input_text = system_prompt + plan
    input_tokens = count_tokens(input_text)
    answer = agent_ReAct.chat(plan)
    output_tokens = count_tokens(answer.response)
    return answer.response, input_tokens, output_tokens


def invoke(prompt, temperature=0.0, max_tokens=4000):
    """
    Generates a response from a language model based on the given prompt.

    Args:
        prompt (str): The input text to generate a response for.
        temperature (float, optional): The sampling temperature to use. Defaults to 0.0.
        max_tokens (int, optional): The maximum number of tokens to generate. Defaults to 8000.

    Returns:
        tuple: A tuple containing:
            - answer (str): The generated response text.
            - input_token (int): The number of tokens in the input prompt.
            - output_token (int): The number of tokens in the generated response.
    """
    response = get_llm().complete(
        prompt, image_documents=None, max_tokens=max_tokens
    )
    input_token = response.raw.usage.prompt_tokens
    output_token = response.raw.usage.completion_tokens
    answer = response.text
    return answer, input_token, output_token


def chat_invoke(history, temperature=0.0, max_tokens=4000):
    """
    Invokes a chat response from the LLM (Language Learning Model) based on the provided history.

    Parameters:
    history (list): A list of previous messages to provide context for the chat.
    temperature (float, optional): The sampling temperature to use. Higher values mean the model will take more risks. Defaults to 0.0.
    max_tokens (int, optional): The maximum number of tokens to generate in the response. Defaults to 8000.

    Returns:
    tuple: A tuple containing:
        - answer (str): The content of the response message.
        - input_token (int): The number of tokens used in the prompt.
        - output_token (int): The number of tokens used in the completion.
    """
    response = get_llm().chat(history, max_tokens=max_tokens)
    input_token = response.raw.usage.prompt_tokens
    output_token = response.raw.usage.completion_tokens
    answer = response.message.content
    return answer, input_token, output_token


def base64_to_image_document(base64_image, image_mimetype="image/png", caption=None):
    """
    Convert Base64-encoded image to ImageDocument and save it in a folder.

    Args:
        base64_image (str): Base64-encoded image string.
        image_mimetype (str): MIME type of the image (e.g., 'image/png').
        caption (str): Caption for the image.

    Returns:
        ImageDocument: The decoded image as an ImageDocument.
    """
    image_data = base64.b64decode(base64_image)

    # Ensure the folder exists
    folder_path = "temp_images"
    os.makedirs(folder_path, exist_ok=True)

    # Create a unique file in the folder
    temp_file = tempfile.NamedTemporaryFile(
        delete=False, suffix=".png", dir=folder_path
    )
    temp_file.write(image_data)
    temp_file.close()

    image_document = ImageDocument(image_path=temp_file.name)
    temp_files_paths.append(temp_file.name)
    return image_document


def ask_ddg(prompt: str, history: list):
    if history:
        history_str = "\n".join(
            [
                f"User: {question_answer['question']}\n Assistant: {question_answer['answer']}"
                for question_answer in history
            ]
        )
        prompt = f"{prompt}\n\n{history_str}"
    try:
        chat_result = get_agent().chat(prompt)
        res = chat_result.response
        print(res)
        return res
    except Exception as e:
        print(f"error in ddg calling : {e}")
        return None


def delete_image():
    for tmp in temp_files_paths:
        os.remove(tmp)
    temp_files_paths.clear()


def get_crypto_day_data(currency_type, resolution="1D", length_of_period=50):
    """
    Fetches daily cryptocurrency data from the ChartCenter API.

    Args:
        currency type is dictionary
        from_timestamp (int): The starting timestamp for the data. Default is 1704499200.
        to_timestamp (int): The ending timestamp for the data. Default is 1733011200.

    Returns:
        list: A list of dictionaries containing the processed data, or an error message.

    Example URL:
        https://api.chartcenter.ir/t-view/4b36ba340386779792411a43990d4319/bars?symbol=crypto@BTC&resolution=1D&from=1704499200&to=1733011200&countback=330
    """
    url = f"https://api.chartcenter.ir/t-view/4b36ba340386779792411a43990d4319/bars"
    to_timestamp = int(time.time())

    market = currency_type.get("market")
    pair = currency_type.get("pair")
    if market == "crypto:spot":
        params = {
            "symbol": f"crypto@{pair}",
            "resolution": resolution,
            "to": to_timestamp,
            "countback": length_of_period,
        }
        price_history = get_request(url=url, params=params)
        return price_history
    elif market == "forex":
        params = {
            "symbol": f"forex@{pair}",
            "resolution": resolution,
            "to": to_timestamp,
            "countback": length_of_period,
        }
        return get_request(url=url, params=params)

    elif market == "stock":
        params = {
            "symbol": "فملی",
            "resolution": resolution,
            "to": to_timestamp,
            "countback": length_of_period,
        }
        price_history = get_request(url=url, params=params)
        return price_history


def parse_json_answer(response):
    if "}" not in response:
        return response
    start_index = response.find("{")
    end_index = response.rfind("}")
    response = response[start_index : end_index + 1]
    response = literal_eval(response)
    return response


def get_and_parse_steps(steps):
    if steps and "steps" in list(steps.keys()):
        steps = steps["steps"]
        return steps
    else:
        raise ValueError("Non valid format for steps")


def parse_list_answer(response: str):
    if "]" not in response:
        return response
    start_index = response.find("[")
    end_index = response.rfind("]")
    return response[start_index : end_index + 1]


def switch_case_resolution(resolution):
    if not resolution:
        return ""
    param = resolution[-1]
    interval = resolution[:-1]
    match param:
        case "m":
            return f"{interval}_minute_intervals"
        case "h":
            return f"{interval}_hour_intervals"
        case "d":
            return f"{interval}_day_intervals"
        case "w":
            return f"{interval}_weekly_intervals"
        case "M":
            return f"{interval}_monthly_intervals"
        case _:
            return ""


def extract_code(response):
    if "```" not in response:
        return response
    start_index = response.find("```")
    end_index = response.rfind("```")
    response = response[start_index : end_index + 3]
    return response


def get_request(url, params):
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            price_history = response.json()
            price_history = [
                f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(history['time']))} :\n Open: {history['open']}, High: {history['high']}, Low: {history['low']}, Close: {history['close']}, Volume: {history['volume']}"
                for history in price_history
            ]

        return "\n-----\n".join(price_history)

    except requests.exceptions.RequestException as e:
        raise RuntimeError(
            f"An error occurred during the GET request: {e}, status code : {response.status_code()}"
        )


def make_human_readable_indicators(data):
    values = []
    if data and isinstance(data, list):
        for d in data:
            if isinstance(d, list):
                if isinstance(d[0], int):
                    values.append(
                        f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(d[0] / 1000))}"
                        + f": {d[1]}"
                    )
                elif isinstance(d[0], str) and d[0].isdigit():
                    d[0] = int(d[0])
                    values.append(
                        f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(d[0] / 1000))}"
                        + f": {d[1]}"
                    )
            else:
                continue
    return "\n".join(values)


def make_human_readable(tools, mode=True):
    if tools:
        if not mode:
            if isinstance(tools, str) and str.isdigit(str(tools)):
                tools = int(tools)
                return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(tools))
            elif isinstance(tools, int):
                return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(tools))
        if isinstance(tools, list):
            make_human_readable_list = []
            if isinstance(tools[0], dict):
                for tool in tools:
                    for key, value in tool.items():
                        if "time" in key.lower():
                            if isinstance(value, int):
                                value /= 1000
                                make_human_readable_list.append(
                                    f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(value))} :\n Open: {tool.get('open', None)}, High: {tool.get('high', None)}, Low: {tool.get('low', None)}, Close: {tool.get('close', None)}, Volume: {tool.get('volume')}"
                                )
                            elif isinstance(value, str) and str.isdigit(value):
                                value = int(value) / 1000
                                make_human_readable_list.append(
                                    f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(value))} :\n Open: {tool.get('open', None)}, High: {tool.get('high', None)}, Low: {tool.get('low', None)}, Close: {tool.get('close', None)}, Volume: {tool.get('volume')}"
                                )
                            else:
                                make_human_readable_list.append(
                                    f"{time.strftime(value)} :\n Open: {tool.get('open', None)}, High: {tool.get('high', None)}, Low: {tool.get('low', None)}, Close: {tool.get('close', None)}, Volume: {tool.get('volume')}"
                                )

            return "\n-----\n".join(make_human_readable_list)
    return tools


def leakage_detection(answer):
    if answer.lower().strip() in [
        "متأسفانه، نمی‌توانم به درخواست شما پاسخ دهم",
        "i'm sorry, but i can't assist with that.",
    ]:
        return True, 0, 0

    prompt = leakage_detection_prompt.format(response=answer)
    detected_leakage, input_tokens, output_tokens = invoke(prompt=prompt)
    if "yes" in detected_leakage.lower():
        return True, input_tokens, output_tokens
    elif "no" in detected_leakage.lower():
        return False, input_tokens, output_tokens
    else:
        return False, input_tokens, output_tokens


def remove_unwanted_text(answer):
    lines = answer.strip().split("\n")

    if lines:
        first_line = re.sub(r"[a-zA-Z.]", "", lines[0]).strip()
        lines[0] = first_line

    cleaned_answer = "\n".join(lines)

    unwanted_phrases = [
        "i can write based on the analysis of the available indicators and market data:",
        "i can write an analysis based on the available data and indicators for",
        "i can write an analysis based on the provided data for",
        "i can write.an analysis based on the available data and indicators for",
        "i can writean analysis based on the available data and indicators for",
        "an analysis based on the available data and indicators for",
        "based on the analysis of the available indicators and market data:",
        "i can write an analysis based on the provided data for",
        "an analysis based on the available indicators and data for"
        "based on"
        "i can write.",
        "i can write",
    ]
    cleaned_answer = cleaned_answer.lower()
    for phrase in unwanted_phrases:
        if phrase in cleaned_answer:
            cleaned_answer = cleaned_answer.replace(phrase, "")
    return cleaned_answer.upper().strip()
