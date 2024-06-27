from typing import List, Tuple, Optional, Dict, Set
import logging
import re
import json
import datetime
import subprocess
import time
import asyncio
from aiohttp import ClientSession, ClientError, ClientTimeout
from bs4 import BeautifulSoup

# Polling Configuration
SIGNAL_POLLING_INTERVAL = 2  # seconds

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("app.log"), logging.StreamHandler()],
)


class Application:
    """
    Manages the global state of the application.

    This class serves as a central point for storing and accessing
    the SentinelGPT instance used throughout the application.
    """

    def __init__(self):
        """Initialize the Application instance."""
        self.sentinel_gpt = None

    def set_sentinel_gpt(self, sentinel_gpt):
        """Set the sentinel_gpt attribute."""
        self.sentinel_gpt = sentinel_gpt

    def get_sentinel_gpt(self):
        """Get the sentinel_gpt attribute."""
        return self.sentinel_gpt


app = Application()


class GameStateMonitor:
    """
    Monitors game states and sends notifications for changes.

    This class is responsible for fetching game pages, extracting game states,
    and notifying users of any changes in the game state.
    """

    def __init__(self, config: Dict):
        """Initialize the GameStateMonitor with configuration."""
        self.config = config
        self.game_states = {}
        self.game_states_lock = asyncio.Lock()

    async def fetch_game_page(
        self, url: str, timeout: int = 30, retries: int = 3
    ) -> Optional[str]:
        """
        Fetch the HTML content of a game page.

        Args:
            url(str): The URL of the game page to fetch.
            timeout(int): Timeout for the request in seconds.
            retries(int): Number of retry attempts.

        Returns:
            Optional[str]: The HTML content of the page if successful, None otherwise.
        """
        logging.debug("Querying game page: %s", url)
        for attempt in range(retries):
            try:
                async with ClientSession() as session:
                    async with session.get(
                        url, timeout=ClientTimeout(total=timeout)
                    ) as response:
                        response.raise_for_status()
                        html = await response.text()
                        logging.info("Successfully queried game page: %s", url)
                        return html
            except (ClientError, asyncio.TimeoutError) as e:
                logging.error(
                    "Error querying %s: %s (Attempt %d/%d)",
                    url,
                    e,
                    attempt + 1,
                    retries,
                )
                await asyncio.sleep(2**attempt)
        logging.error(
            "Failed to query game page: %s after %d attempts", url, retries)
        return None

    def extract_game_state(self, html: str) -> Optional[Dict]:
        """
        Extract game state information from HTML content.

        Args:
            html(str): The HTML content of the game page.

        Returns:
            Optional[Dict]: A dictionary containing the extracted game state information,
                          or None if extraction fails.
        """
        logging.debug("Parsing game state...")
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table", class_="basictab")
        if not table:
            logging.error("Error: Game state table not found.")
            return None

        rows = table.find_all("tr")
        if not rows:
            logging.error("Error: No rows found in game state table.")
            return None

        game_state = {}
        game_info = (
            rows[0]
            .find_all("td")[0]
            .get_text()
            .replace("_", " ")
            .replace("turn", "Turn")
        )
        game_state["game_info"] = game_info.strip()
        game_state["players"] = []
        for row in rows[1:]:
            cells = row.find_all("td")
            if len(cells) < 2:
                continue
            faction = cells[0].get_text().strip()
            status = cells[1].get_text().strip()
            game_state["players"].append(
                {"faction": faction, "status": status})

        turn_match = re.search(r", Turn (\d+)", game_info)
        game_state["turn"] = turn_match.group(1) if turn_match else "Unknown"

        logging.info("Game state parsed successfully: %s", game_state)
        return game_state

    async def check_game_and_notify(self, game: Dict):
        try:
            logging.info(f"Starting game state check for game: {game['url']}")
            url = game["url"]

            html = await self.fetch_game_page(url)
            if html is None:
                logging.error(f"Failed to fetch game page for URL: {url}")
                return
            logging.info(f"Successfully fetched game page for URL: {url}")

            current_state = self.extract_game_state(html)
            if current_state is None:
                logging.error(f"Failed to extract game state for URL: {url}")
                return
            logging.info(f"Successfully extracted game state for URL: {url}")

            async with self.game_states_lock:
                last_state = self.game_states.get(url, {}).get("state")
                logging.info(f"Last state: {last_state}")
                logging.info(f"Current state: {current_state}")

                moved_factions = []
                state_changed = False
                if last_state:
                    for last_player, current_player in zip(last_state["players"], current_state["players"]):
                        if last_player["status"] != current_player["status"]:
                            state_changed = True
                            if last_player["status"] == "-" and current_player["status"] == "Turn played":
                                moved_factions.append(
                                    current_player["faction"])
                                logging.info(
                                    f"Faction {current_player['faction']} has moved")
                else:
                    logging.info(
                        "No last state available, this might be the first check")

                if state_changed:
                    logging.info(
                        "State change detected, preparing notifications")
                    # ... (rest of the notification logic)
                else:
                    logging.info("No state change detected")

                self.game_states[url] = {
                    "state": current_state,
                    "last_change_time": datetime.datetime.now(),
                }

            logging.info(f"Game state check completed for game: {game['url']}")
        except Exception as e:
            logging.error(
                f"Unexpected error in check_game_and_notify for game {game['url']}: {e}", exc_info=True)


class SentinelGPTProcessManager:
    """
    Manages the SentinelGPT subprocess.

    This class handles starting, monitoring, and interacting with the SentinelGPT
    subprocess, which is used for processing complex commands.
    """

    def __init__(self, command: List[str], config: Dict):
        """
        Initialize the SentinelGPTProcessManager with a command and configuration.
        """
        self.command = command
        self.config = config
        self.process = None
        self.subprocess_lock = asyncio.Lock()
        self.known_assistants = {}

    async def start_process(self):
        logging.info("Starting SentinelGPT process...")
        try:
            self.process = await asyncio.create_subprocess_exec(
                *self.command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.config.get("gpt_directory", "."),
            )
            if self.process:
                asyncio.create_task(self.log_errors())
                logging.info("SentinelGPT process started.")
                await self.get_known_assistants()
        except (OSError, subprocess.SubprocessError) as e:
            logging.error("Failed to start SentinelGPT process: %s", e)

    async def log_errors(self):
        try:
            while True:
                line = await self.process.stderr.readline()
                if not line:
                    break
                logging.error("SentinelGPT stderr: %s", line.decode().strip())
        except Exception as e:
            logging.error("Error logging SentinelGPT stderr: %s", e)

    async def get_known_assistants(self):
        self.process.stdin.write(b"GET_ASSISTANTS\n")
        await self.process.stdin.drain()
        response = await self.process.stdout.readline()
        self.known_assistants = json.loads(response.decode().strip())
        logging.info(f"Received known assistants: {self.known_assistants}")

    async def wait_for_initialization(self, timeout: int = 30):
        """
        Wait for the SentinelGPT process to initialize and populate known assistants.
        """
        start_time = time.time()
        while not self.known_assistants and time.time() - start_time < timeout:
            await asyncio.sleep(1)
            await self.get_known_assistants()
        if not self.known_assistants:
            logging.warning(
                f"SentinelGPT initialization timed out after {timeout} seconds")
        else:
            logging.info("SentinelGPT initialized successfully")

    async def restart_process(self):
        """
        Restart the SentinelGPT process if necessary.
        This method ensures thread-safe restarting of the process.
        """
        logging.info("Restarting SentinelGPT process...")
        async with self.subprocess_lock:
            if self.process:
                logging.debug("Terminating existing process...")
                self.process.terminate()
                try:
                    await asyncio.wait_for(self.process.wait(), timeout=10)
                except asyncio.TimeoutError:
                    logging.warning(
                        "Process didn't terminate gracefully. Killing it.")
                    self.process.kill()
                    await self.process.wait()

            logging.debug("Starting new SentinelGPT process...")
            try:
                self.process = await asyncio.create_subprocess_exec(
                    *self.command,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=self.config.get("gpt_directory", "."),
                )
                if self.process:
                    asyncio.create_task(self.log_errors())
                    logging.info("SentinelGPT process restarted successfully.")
                    await self.get_known_assistants()
                else:
                    logging.error("Failed to restart SentinelGPT process.")
            except (OSError, subprocess.SubprocessError) as e:
                logging.error(f"Error restarting SentinelGPT process: {e}")
                self.process = None

            if not self.process:
                logging.error("SentinelGPT process restart failed.")

    async def process_messages(self, messages: List[str], timeout: int = 30):
        responses = []
        for message in messages:
            try:
                # We'll only pass the message to process_single_message
                response = await self.process_single_message(message)
                responses.append(response)
            except asyncio.TimeoutError:
                logging.error("Timeout processing message: %s", message)
                responses.append("Error: Command processing timed out")
            except Exception as e:
                logging.error(
                    "Error processing message: %s. Error: %s", message, str(e))
                responses.append(f"Error: {str(e)}")
        return responses

    async def process_single_message(self, message: str) -> str:
        logging.debug(f"Attempting to send message to SentinelGPT: {message}")

        try:
            logging.debug(f"Writing message to SentinelGPT stdin: {message}")
            self.process.stdin.write(f"{message}\n".encode())
            logging.debug("Message written, now draining stdin")
            await self.process.stdin.drain()
            logging.debug("Message sent to SentinelGPT successfully")
        except Exception as e:
            logging.error(
                f"Error sending message to SentinelGPT: {e}", exc_info=True)
            raise

        logging.debug("Waiting for response from SentinelGPT")
        try:
            response = await self._read_response()
            logging.debug(f"Received response from SentinelGPT: {response}")
            return response
        except Exception as e:
            logging.error(f"Error reading response from SentinelGPT: {e}")
            raise

    async def _read_response(self):
        response_lines = []
        while True:
            try:
                line = await asyncio.wait_for(self.process.stdout.readline(), timeout=10.0)
                logging.debug(f"Read line from SentinelGPT: {line}")
                if line.endswith(b"##END##\n"):
                    response_lines.append(line[:-7])
                    break
                response_lines.append(line)
            except asyncio.TimeoutError:
                logging.error(
                    "Timeout while reading response from SentinelGPT")
                break
            except Exception as e:
                logging.error(f"Error reading line from SentinelGPT: {e}")
                break
        return b"".join(response_lines).decode().strip()

    async def check_health(self):
        if self.process is None or self.process.returncode is not None:
            logging.warning(
                "SentinelGPT process is not running. Restarting...")
            await self.start_process()


def extract_group_info(msg: str) -> Tuple[Optional[str], Optional[str]]:
    group_id = None
    group_name = None

    lines = msg.split('\n')
    for line in lines:
        stripped_line = line.strip()
        if stripped_line.startswith("Id:"):
            group_id = stripped_line.split("Id:", 1)[1].strip()
            logging.debug(f"Extracted group ID: {group_id}")
        elif stripped_line.startswith("Name:"):
            group_name = stripped_line.split("Name:", 1)[1].strip()
            logging.debug(f"Extracted group name: {group_name}")

        if group_id and group_name:
            break

    if not group_id:
        logging.warning("Failed to extract group ID from message")
    if not group_name:
        logging.warning("Failed to extract group name from message")

    return group_id, group_name


def load_and_validate_config(config_path: str = "config.json") -> Dict:
    logging.debug("Loading configuration...")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        required_keys = ["phone_number",
                         "allowed_group_ids", "games", "gpt_directory"]
        missing_keys = [key for key in required_keys if key not in config]
        if missing_keys:
            raise ValueError(
                f"Config missing required keys: {', '.join(missing_keys)}")

        if not isinstance(config["phone_number"], str) or not re.match(r"^\+?\d+$", config["phone_number"]):
            raise ValueError("Invalid phone_number in configuration")

        if not isinstance(config["allowed_group_ids"], list) or not all(isinstance(gid, str) for gid in config["allowed_group_ids"]):
            raise ValueError("Invalid allowed_group_ids in configuration")

        if not isinstance(config["games"], list) or not all(isinstance(game, dict) for game in config["games"]):
            raise ValueError("Invalid games list in configuration")

        if not isinstance(config["gpt_directory"], str):
            raise ValueError("Invalid gpt_directory in configuration")

        logging.info("Configuration loaded and validated successfully.")
        return config
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
        logging.error("Error loading configuration: %s", e)
        raise


async def send_signal_message(
    phone_number: str,
    group_id: str,
    message: str,
    mentions: Optional[List[Dict]] = None,
    timeout: int = 30,
):
    logging.debug(f"Sending Signal message to group {group_id}")
    if not message.strip():
        logging.debug("Message is empty, not sending.")
        return

    command = [
        "docker",
        "exec",
        "signal-api",
        "signal-cli",
        "-u",
        phone_number,
        "send",
        "-g",
        group_id,
        "-m",
        message,
    ]
    if mentions:
        for mention in mentions:
            command.extend([
                "--mention",
                f"{mention['start']}:{mention['length']}:{mention['phone_number']}",
            ])

    logging.debug(f"Executing command: {' '.join(command)}")
    status, output = await asyncio.to_thread(execute_subprocess_with_retries, command, timeout)

    if status:
        logging.info(f"Message sent successfully to group {group_id}")
    else:
        logging.error(f"Failed to send message to group {group_id}: {output}")


def execute_subprocess_with_retries(
    command: List[str], timeout: int = 60, retries: int = 3
) -> Tuple[bool, List[str]]:
    """
    Execute a subprocess command with retries.

    Args:
        command (List[str]): Command to execute as a list of strings.
        timeout (int): Timeout for each attempt in seconds.
        retries (int): Number of retry attempts.

    Returns:
        Tuple[bool, List[str]]: A tuple containing a success flag and the command output as a
        list of strings.
    """
    for attempt in range(retries):
        try:
            result = subprocess.run(
                command, capture_output=True, text=True, timeout=timeout, check=True
            )
            return True, result.stdout.strip().split("\n")
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, OSError) as e:
            logging.error(
                "Error running command %s: %s (Attempt %d/%d)",
                " ".join(command),
                e,
                attempt + 1,
                retries,
            )
        time.sleep(2**attempt)
    return False, []


async def receive_signal_messages(phone_number: str, config: Dict):
    logging.debug("Starting to receive messages...")
    command = [
        "docker",
        "exec",
        "signal-api",
        "signal-cli",
        "-a",
        phone_number,
        "receive",
        "--ignore-attachments",
    ]

    while True:
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Capture both stdout and stderr
            stdout, stderr = await process.communicate()

            if stdout:
                messages = stdout.decode().splitlines()
                await process_signal_messages(messages, phone_number, config)

            # Log the stderr output
            if stderr:
                logging.error(f"signal-cli stderr: {stderr.decode()}")

            # Check if the process has exited
            return_code = process.returncode
            if return_code != 0:
                logging.error(
                    f"signal-cli process exited with return code {return_code}")

        except asyncio.CancelledError:
            logging.info("Receive messages task was cancelled")
            break
        except Exception as e:
            logging.error(f"Error in receive_signal_messages: {e}")

        # Wait before retrying
        await asyncio.sleep(SIGNAL_POLLING_INTERVAL)


async def process_signal_messages(messages: List[str], phone_number: str, config: Dict):
    logging.info(f"Received {len(messages)} message lines.")
    sentinel_gpt = app.get_sentinel_gpt()
    allowed_group_ids = set(config.get("allowed_group_ids", []))
    logging.debug(f"Allowed group IDs: {allowed_group_ids}")

    current_message = []
    for line in messages:
        logging.debug(f"Processing line: {line}")
        current_message.append(line)

        if line.strip() == "":  # Empty line indicates end of a message
            # Process the complete message
            await process_complete_message(current_message, phone_number, config, sentinel_gpt, allowed_group_ids)
            # Reset for next message
            current_message = []

    # Process any remaining message
    if current_message:
        await process_complete_message(current_message, phone_number, config, sentinel_gpt, allowed_group_ids)

    logging.info(f"Finished processing {len(messages)} message lines")


async def process_complete_message(current_message: List[str], phone_number: str, config: Dict, sentinel_gpt, allowed_group_ids: Set[str]):
    group_id, group_name, body = extract_message_info(current_message)

    logging.debug(
        f"Extracted message info - Group ID: {group_id}, Group Name: {group_name}, Body: {body}")

    if body and body.startswith("!"):
        if group_id is None:
            logging.warning(f"Command message without group ID: {body}")
        elif group_id not in allowed_group_ids:
            logging.warning(
                f"Command message from non-allowed group: {group_id}")
        else:
            logging.info(
                f"Processing command message: {body} for group: {group_id}")
            try:
                await process_command_message(
                    current_message,
                    phone_number,
                    config,
                    sentinel_gpt,
                    group_id,
                    body,
                )
                logging.debug("Command processed successfully")
            except Exception as e:
                logging.error(f"Error processing command: {e}")
    else:
        logging.debug("Message does not contain a command, skipping")


def extract_message_info(message_lines: List[str]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    group_id = None
    group_name = None
    body = None
    is_sync_message = False

    for i, line in enumerate(message_lines):
        stripped_line = line.strip()

        if stripped_line == "Received sync sent message":
            is_sync_message = True

        elif stripped_line.startswith("Body:"):
            if not is_sync_message:
                body = stripped_line.split("Body:", 1)[1].strip()

        elif "Group info:" in stripped_line:
            group_info = "\n".join(message_lines[i:])
            group_id, group_name = extract_group_info(group_info)

        elif is_sync_message and stripped_line.startswith("Message timestamp:"):
            next_line = message_lines[i + 1].strip() if i + \
                1 < len(message_lines) else ""
            if next_line.startswith("Body:"):
                body = next_line.split("Body:", 1)[1].strip()

    return group_id, group_name, body


async def process_command_message(
    message_lines: List[str],
    phone_number: str,
    config: Dict,
    sentinel_gpt,
    group_id: str,
    body: str,
):
    logging.info(f"Processing command message: {body}")
    parts = body.split(maxsplit=1)
    if len(parts) == 2:
        prefix, command = parts
        prefix = prefix.lstrip("!")

        if prefix.lower() in sentinel_gpt.known_assistants:
            logging.info(f"Command for assistant '{prefix}': {command}")
            try:
                async with sentinel_gpt.subprocess_lock:
                    responses = await sentinel_gpt.process_messages([f"{prefix} {command}"])

                if responses:
                    for response in responses:
                        formatted_response = f"THE MACHINE HAS RETURNED WITH THE ANSWERS YOU SEEK\n\n{response}"
                        logging.info(f"Sending response for command: {body}")
                        await send_signal_message(phone_number, group_id, formatted_response)
                        logging.info(f"Response sent for command: {body}")
                else:
                    logging.warning(
                        f"No response generated for command: {body}")
                    await send_signal_message(phone_number, group_id, "No response was generated for your command.")
            except Exception as e:
                logging.error(
                    f"Error processing command with SentinelGPT: {e}", exc_info=True)
                error_message = f"Error processing command: {str(e)}"
                await send_signal_message(phone_number, group_id, error_message)
        elif prefix == "status":
            # Handle status command (no changes needed here)
            pass
        else:
            logging.warning(f"Unknown command prefix: {prefix}")
            await send_signal_message(phone_number, group_id, f"Unknown command: {prefix}")
    else:
        logging.warning(f"Invalid command format: {body}")
        await send_signal_message(phone_number, group_id, "Invalid command format. Please use '!command argument'.")


async def send_message_responses(
    phone_number: str, group_id: str, messages: List[str], responses: List[str]
):
    for message, response in zip(messages, responses):
        if response:
            logging.info(f"Sending response for message: {message[:50]}...")
            await send_signal_message(phone_number, group_id, response)
            logging.info(f"Response sent for message: {message[:50]}...")
        else:
            logging.warning(
                f"No response generated for message: {message[:50]}...")


async def periodic_check(game_monitor: GameStateMonitor, game: Dict, interval: int):
    while True:
        logging.info(f"Running periodic check for game: {game['url']}")
        try:
            await game_monitor.check_game_and_notify(game)
            logging.info(f"Periodic check completed for game: {game['url']}")
        except Exception as e:
            logging.error(
                f"Error during periodic check for game {game['url']}: {e}", exc_info=True)

        logging.info(f"Sleeping for {interval} seconds before next check")
        await asyncio.sleep(interval)


async def handle_status_command(phone_number: str, config: Dict, group_id: str) -> None:
    """
    Handle the !status command by polling the website and returning the status message.

    Args:
        phone_number (str): Phone number to send the status message from.
        config (Dict): Configuration dictionary.
        group_id (str): ID of the group to send the status message to.
    """
    logging.info("Handling !status command")
    game_monitor = GameStateMonitor(config)
    status_messages = []

    for game in config["games"]:
        html = await game_monitor.fetch_game_page(game["url"])
        if html is None:
            status_messages.append(
                f"Unable to fetch game state for {game['url']}")
            continue

        state = game_monitor.extract_game_state(html)
        if state:
            game_info_parts = state["game_info"].split(",")
            game_name = game_info_parts[0].strip()
            turn_number = next(
                (part.strip() for part in game_info_parts if "Turn" in part),
                "Unknown Turn",
            )

            outstanding_players = [
                player
                for player in state["players"]
                if player["status"] == "-"
                and game["players"].get(player["faction"], {}).get("name") != "CPU"
            ]

            status_message = f"Current game state for {game_name}, {turn_number}:"

            if outstanding_players:
                status_message += "\nOutstanding Players:"
                for player in outstanding_players:
                    status_message += f"\n{player['faction']}: {player['status']}"
            else:
                status_message += "\nNo outstanding human players at the moment."
        else:
            status_message = f"Unable to parse game state for {game['url']}"

        status_messages.append(status_message)

    combined_status = "\n\n".join(status_messages)

    await send_signal_message(phone_number, group_id, combined_status)


async def send_intro_message(phone_number: str, config: Dict, known_assistants: dict):
    allowed_group_ids = config.get("allowed_group_ids", [])

    for group_id in allowed_group_ids:
        intro_message = (
            "THE MACHINE IS NOW AWAITING YOUR REQUESTS.\nAvailable commands:"
        )
        intro_message += "\n!status - Check the status of ongoing games"

        for assistant in known_assistants.keys():
            intro_message += (
                f"\n!{assistant} - Message the {assistant.capitalize()} assistant"
            )

        await send_signal_message(phone_number, group_id, intro_message)

        # Send status message separately
        await handle_status_command(phone_number, config, group_id)


async def main():
    logging.info("Starting main function...")
    receive_task = None
    sentinel_gpt = None
    check_tasks = []

    try:
        config = load_and_validate_config()

        sentinelgpt_command = [
            "bash",
            "-c",
            "source venv/bin/activate && python sentinelgpt.py",
        ]

        sentinel_gpt: SentinelGPTProcessManager = SentinelGPTProcessManager(
            sentinelgpt_command, config)
        app.set_sentinel_gpt(sentinel_gpt)
        await sentinel_gpt.start_process()

        # Wait for SentinelGPT to initialize
        await sentinel_gpt.wait_for_initialization(timeout=30)

        if not sentinel_gpt.known_assistants:
            logging.error(
                "Failed to initialize SentinelGPT and retrieve known assistants.")
            return

        # Send the introductory message with status
        await send_intro_message(config["phone_number"], config, sentinel_gpt.known_assistants)

        game_monitor = GameStateMonitor(config)

        # Create tasks for periodic checks
        for game in config["games"]:
            task = asyncio.create_task(periodic_check(
                game_monitor, game, 300))  # 300 seconds = 5 minutes
            check_tasks.append(task)

        receive_task = asyncio.create_task(
            receive_signal_messages(config["phone_number"], config))

        while True:
            await asyncio.sleep(1)
            await sentinel_gpt.check_health()

    except asyncio.CancelledError:
        logging.info("Main loop cancelled, shutting down...")
    except KeyboardInterrupt:
        logging.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logging.error(f"Unexpected error in main loop: {e}", exc_info=True)
    finally:
        logging.info("Cleaning up resources...")
        if receive_task:
            receive_task.cancel()
            try:
                await receive_task
            except asyncio.CancelledError:
                pass
        for task in check_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        if sentinel_gpt and sentinel_gpt.process:
            sentinel_gpt.process.stdin.close()
            sentinel_gpt.process.terminate()
            await sentinel_gpt.process.wait()
            logging.info("SentinelGPT process terminated.")

# Run the main function
if __name__ == "__main__":
    asyncio.run(main())
