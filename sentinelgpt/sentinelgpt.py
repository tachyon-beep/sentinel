import argparse
import logging
import os
import sys
import time
import json
from typing import Optional, Any, Dict
from openai import OpenAI, OpenAIError, AuthenticationError, RateLimitError, AssistantEventHandler
from dotenv import load_dotenv

THREAD_ARCHIVE_TIMEOUT = 300  # Timeout in seconds (5 minutes)
IDLE_LOOP_DELAY = 0.1  # Delay in seconds to prevent excessive CPU usage when idle


def configure_logging(log_level: str = 'INFO') -> None:
    """Set up logging configuration with console and file handlers."""
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {log_level}')

    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)

    file_handler = logging.FileHandler('sentinelgpt.log', mode='a')
    file_handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


def load_environment_variables() -> None:
    """Load environment variables from .env file."""
    if not os.path.exists(".env"):
        logging.error("No .env file found.")
        sys.exit(1)
    else:
        load_dotenv()
        logging.info("Loaded .env file successfully.")


def get_assistants() -> Dict[str, str]:
    """Retrieve the assistants from environment variables."""
    assistants_json = os.getenv("ASSISTANTS")
    if not assistants_json:
        logging.error("ASSISTANTS is not set in the .env file.")
        return {}

    try:
        assistants = json.loads(assistants_json)
        logging.info(f"Assistants loaded: {assistants}")
        return assistants
    except json.JSONDecodeError:
        logging.error("ASSISTANTS in .env file is not valid JSON.")
        return {}


def get_assistant_id(prefix: str) -> str:
    """Retrieve the assistant ID based on the prefix."""
    assistants = get_assistants()
    assistant_id = assistants.get(prefix)
    if not assistant_id:
        logging.error(f"No assistant ID found for prefix '{prefix}'.")
        sys.exit(1)

    return assistant_id


def parse_cli_arguments() -> argparse.Namespace:
    """Parse command-line arguments for the assistant script."""
    parser = argparse.ArgumentParser(
        description='Assistant script to process messages.')
    parser.add_argument('--log_level', type=str, default='INFO',
                        help='Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)')
    parser.add_argument('--message', type=str, help='Message to process')
    return parser.parse_args()


def initialize_openai_client() -> OpenAI:
    """Initialize and return the OpenAI client."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logging.error("OPENAI_API_KEY environment variable is not set.")
        sys.exit(1)

    try:
        return OpenAI(api_key=api_key)
    except OpenAIError as openai_error:
        logging.error("Failed to create OpenAI client: %s", openai_error)
        sys.exit(1)


class ResponseHandler(AssistantEventHandler):
    """Handler for processing responses from the OpenAI API."""

    def __init__(self, api_client: OpenAI, thread_id: Optional[str]) -> None:
        super().__init__()
        self.api_client = api_client
        self.accumulated_response = ""
        self.thread_id = thread_id

    def on_text_created(self, text: str) -> None:
        logging.info("Assistant > %s", text)

    def on_text_delta(self, delta: Any, snapshot: Any) -> None:
        if hasattr(delta, 'value'):
            self.accumulated_response += delta.value
            logging.debug("Delta value received: %s", delta.value)
        else:
            logging.warning("Received non-string delta: %s", delta)

    def get_formatted_response(self) -> str:
        """Return the accumulated response with a delimiter."""
        return f"{self.accumulated_response}\n##END##"


def manage_conversation_thread(api_client: OpenAI, current_thread_id: Optional[str],
                               last_interaction_time: float) -> tuple[str, float]:
    """Create a new thread or retrieve an existing one based on the timeout."""
    current_time = time.time()
    if current_thread_id and (current_time - last_interaction_time < THREAD_ARCHIVE_TIMEOUT):
        logging.debug("Reusing existing thread ID: %s", current_thread_id)
        return current_thread_id, current_time

    if current_thread_id:
        logging.debug(
            "Archiving old thread ID: %s due to inactivity", current_thread_id)
        try:
            archive_conversation_thread(api_client, current_thread_id)
        except OpenAIError as archive_error:
            logging.error("Failed to archive thread: %s", archive_error)

    logging.debug("Creating a new thread.")
    new_thread = api_client.beta.threads.create()
    new_thread_id = new_thread.id
    logging.info("Created new thread with ID: %s", new_thread_id)
    return new_thread_id, current_time


def archive_conversation_thread(api_client: OpenAI, thread_id: str) -> None:
    """Archive the conversation thread."""
    api_client.beta.threads.delete(thread_id)


def process_user_message(user_message: str, prefix: str, client: OpenAI,
                         current_thread_id: Optional[str],
                         last_interaction_time: float) -> tuple[str, str, float]:
    """Process a user message and return the assistant's response."""
    logging.debug("Initializing ResponseHandler.")
    thread_id, current_time = manage_conversation_thread(
        client, current_thread_id, last_interaction_time)
    response_handler = ResponseHandler(client, thread_id)
    try:
        logging.debug("Creating a message in thread: %s", thread_id)
        message = client.beta.threads.messages.create(
            thread_id=thread_id, role="user", content=user_message)

        if hasattr(message, 'content') and message.content:
            processed_content = process_message_annotations(
                client, thread_id, message.id)
            logging.debug("Processed Message Content: %s", processed_content)

        assistant_id = get_assistant_id(prefix)
        logging.debug(
            "Streaming the response using assistant ID: %s", assistant_id)
        with client.beta.threads.runs.stream(
                thread_id=thread_id,
                assistant_id=assistant_id,
                event_handler=response_handler,
        ) as stream:
            stream.until_done()

        logging.info("Assistant response generated successfully.")
        return response_handler.get_formatted_response(), thread_id, current_time
    except AuthenticationError as auth_error:
        logging.error("Authentication error: %s", auth_error)
        return f"Authentication failure: {auth_error}", thread_id, current_time
    except RateLimitError as rate_limit_error:
        logging.error("Rate limit exceeded: %s", rate_limit_error)
        return "Rate limit exceeded.", thread_id, current_time
    except OpenAIError as openai_error:
        logging.error("API error: %s", openai_error)
        return f"API error occurred: {openai_error}", thread_id, current_time
    except TimeoutError:
        logging.error("Timeout error occurred.")
        return "Request timed out, please try again later.", thread_id, current_time
    except (TypeError, KeyError, AttributeError, ValueError) as exception:
        logging.error("An error occurred: %s", exception)
        return "An error occurred processing your request.", thread_id, current_time


def cleanup_resources(client: OpenAI, current_thread_id: Optional[str]) -> None:
    """Clean up resources and archive the conversation thread on shutdown."""
    if current_thread_id:
        try:
            archive_conversation_thread(client, current_thread_id)
            logging.info("Gracefully archived thread ID: %s",
                         current_thread_id)
        except OpenAIError as shutdown_error:
            logging.error(
                "Failed to archive thread during shutdown: %s", shutdown_error)


def process_message_annotations(api_client: OpenAI, thread_id: str, message_id: str) -> str:
    """Process annotations from a message and return formatted content."""
    try:
        message = api_client.beta.threads.messages.retrieve(
            thread_id=thread_id, message_id=message_id)
        message_content = message.content[0].text
        annotations = message_content.annotations
        citations = []
        for index, annotation in enumerate(annotations):
            message_content.value = message_content.value.replace(
                annotation.text, f' [{index}]')
            file_citation = getattr(annotation, 'file_citation', None)
            if file_citation:
                cited_file = api_client.files.retrieve(file_citation.file_id)
                citations.append(
                    f'[{index}] {file_citation.quote} from {cited_file.filename}')
            elif (file_path := getattr(annotation, 'file_path', None)):
                cited_file = api_client.files.retrieve(file_path.file_id)
                citations.append(
                    f'[{index}] Click <here> to download {cited_file.filename}')
        message_content.value += '\n' + '\n'.join(citations)
        return message_content.value
    except OpenAIError as annotation_error:
        logging.error("Failed to process annotations: %s", annotation_error)
        return f"Failed to process annotations: {annotation_error}"


def main() -> int:
    """Main function to orchestrate the conversation process."""
    configure_logging('DEBUG')  # Set to DEBUG for more detailed logging
    load_environment_variables()
    client = initialize_openai_client()
    current_thread_id: Optional[str] = None
    last_interaction_time: float = 0.0

    logging.info(
        "SentinelGPT initialized and listening for input messages on stdin...")

    try:
        for line in sys.stdin:
            user_input = line.strip()
            logging.debug(f"SentinelGPT received input: {user_input}")

            if user_input == "GET_ASSISTANTS":
                assistants = get_assistants()
                response = json.dumps(assistants)
                logging.debug(
                    f"SentinelGPT sending assistants list: {response}")
                print(response, flush=True)
                sys.stdout.flush()
            elif user_input:
                parts = user_input.split(maxsplit=1)
                if len(parts) == 2:
                    prefix, message = parts
                    # Remove the '!' from the prefix
                    prefix = prefix.lstrip('!')
                    logging.info(
                        f"Processing message with prefix '{prefix}': {message}")

                    response, current_thread_id, last_interaction_time = process_user_message(
                        message, prefix, client, current_thread_id, last_interaction_time
                    )

                    logging.debug(f"SentinelGPT sending response: {response}")
                    print(response, flush=True)
                    sys.stdout.flush()
                    logging.info(
                        f"Processed message with prefix '{prefix}', thread ID: {current_thread_id}")
                else:
                    logging.error(f"Invalid input format: {user_input}")
                    print(
                        "Error: Invalid input format. Please use 'prefix message'.", flush=True)
                    sys.stdout.flush()
            else:
                logging.warning("Received empty input, ignoring.")

    except KeyboardInterrupt:
        logging.info("SentinelGPT interrupted by user.")
    except Exception as e:
        logging.error(
            f"An unexpected error occurred in SentinelGPT: {e}", exc_info=True)
    finally:
        cleanup_resources(client, current_thread_id)
        logging.info("SentinelGPT shutting down.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
