import asyncio
from pathlib import Path
from datetime import datetime
import os
import pytz
import aiohttp
import schedule
from aiohttp import ClientSession
from miservice import MiAccount, MiNAService, MiIOService, miio_command
import argparse
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

AM_I_HERE_COMMAND = "2-1078"
TIMEZONE = "Asia/Shanghai"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

if not GITHUB_TOKEN:
    logging.error("GITHUB_TOKEN is not set. Please set the environment variable.")
    raise Exception("GITHUB_TOKEN is not set")

# change it to yours
REPO_NAME = "yihong0618/2025"
UP_ACTION_ID = "135744271"
WORD_ACTION_ID = "135744272"


class MiBoyDaily:
    def __init__(self, account, password, here_did, speaker_did):
        self.mi_session = ClientSession()
        self.account = account
        self.password = password
        self.here_did = here_did
        self.speaker_did = speaker_did
        self.mi_token_home = Path.home() / ".mi.token"

    async def login_miboy(self):
        account = MiAccount(
            self.mi_session,
            self.account,
            self.password,
            str(self.mi_token_home),
        )
        # Forced login to refresh to refresh token
        await account.login("micoapi")
        self.mina_service = MiNAService(account)
        self.miio_service = MiIOService(account)

        # From xiaogpt
        hardware_data = await self.mina_service.device_list()
        # fix multi xiaoai problems we check did first
        # why we use this way to fix?
        # some videos and articles already in the Internet
        # we do not want to change old way, so we check if miotDID in `env` first
        # to set device id

        initial_speaker_did = self.speaker_did
        found_speaker_device = False
        if not initial_speaker_did:
            raise Exception("Speaker device ID (speaker_did) is not provided.")

        for h in hardware_data:
            # Scenario 1: initial_speaker_did is a miotDID, try to find its deviceID
            if h.get("miotDID", "") == str(initial_speaker_did):
                self.speaker_did = h.get("deviceID")
                logging.info(f"Found deviceID {self.speaker_did} for miotDID {initial_speaker_did}")
                found_speaker_device = True
                break
            # Scenario 2: initial_speaker_did is already a deviceID
            elif h.get("deviceID", "") == str(initial_speaker_did):
                # self.speaker_did is already the correct deviceID
                logging.info(f"Provided speaker_did {initial_speaker_did} is a valid deviceID.")
                found_speaker_device = True
                break
        
        if not found_speaker_device:
            # This means the provided initial_speaker_did (whether it was intended as a miotDID or a deviceID)
            # was not found in the hardware_data list.
            raise Exception(
                f"Could not find or resolve speaker device with provided ID: {initial_speaker_did}. "
                f"Please check if it's a correct miotDID or deviceID. Use `micli mina` to list devices."
            )

    async def get_am_i_here(self):
        # 人在传感器的应用 1 为人在 0 为人不在
        try:
            data = await miio_command(
                self.miio_service,
                self.here_did,
                AM_I_HERE_COMMAND,
            )
            return data
        except aiohttp.ClientError as e:
            logging.error(f"Error calling miio_command in get_am_i_here: {e}")
            return None # Or return [] depending on how caller handles it. None seems appropriate.

    async def close(self):
        await self.mi_session.close()

    async def say_good_morning_to_me(self, value):
        try:
            await self.mina_service.text_to_speech(self.speaker_did, value)
        except aiohttp.ClientError as e:
            logging.error(f"Error calling text_to_speech in say_good_morning_to_me: {e}")

    async def call_github_action_workflow(self, action_id=UP_ACTION_ID):
        """
        Trigger GitHub Actions workflow using REST API
        """
        url = f"https://api.github.com/repos/{REPO_NAME}/actions/workflows/{action_id}/dispatches"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {GITHUB_TOKEN}",
        }
        # GitHub Actions API requires a ref
        data = {"ref": "main", "inputs": {"message": "hello"}}  # branch

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                if (
                    response.status == 204
                ):  # GitHub API returns 204 No Content on success
                    logging.info("Successfully triggered workflow")
                    return True
                else:
                    logging.error(f"Failed to trigger workflow: {response.status}")
                    return False

    async def say_hello_to_me_when_i_am_back(self):
        await self.say_good_morning_to_me("早上好") # This already has error handling
        try:
            await self.mina_service.play_by_music_url(
                self.speaker_did, "http://192.168.6.212:8000/public/z1.mp3"
            )
        except aiohttp.ClientError as e:
            logging.error(f"Error calling play_by_music_url in say_hello_to_me_when_i_am_back: {e}")


def parse_args():
    parser = argparse.ArgumentParser(description="MiBoyDaily automation script")
    parser.add_argument(
        "--account", type=str, required=True, help="Mi account email/phone"
    )
    parser.add_argument(
        "--password", type=str, required=True, help="Mi account password"
    )
    parser.add_argument(
        "--here-did", type=str, required=True, help="Device ID for presence detection"
    )
    parser.add_argument(
        "--speaker-did", type=str, required=True, help="Device ID for speaker"
    )
    return parser.parse_args()


async def morning_task(account, password, here_did, speaker_did):
    beijing_tz = pytz.timezone("Asia/Shanghai")
    miboy = MiBoyDaily(
        account=account, password=password, here_did=here_did, speaker_did=speaker_did
    )
    await miboy.login_miboy()

    while True:
        current_time = datetime.now(beijing_tz)
        current_hour = current_time.hour

        # if current hour is after 6 AM, stop the task
        if current_hour >= 7:
            logging.info("After 6 AM, stopping...")
            await miboy.close()
            break

        if current_hour < 4:
            logging.info("Before 4 AM, waiting...")
            await asyncio.sleep(60)
            continue

        data = await miboy.get_am_i_here()
        if data and data[0] == 1: # USER_PRESENT was defined as 1
            # means I get up already
            logging.info("I am up")
            await miboy.say_hello_to_me_when_i_am_back()
            await miboy.call_github_action_workflow()
            await asyncio.sleep(2)
            await miboy.call_github_action_workflow(action_id=WORD_ACTION_ID)
            await miboy.close()
            break
        elif data and data[0] == 0: # USER_NOT_PRESENT was defined as 0
            # means I am sleeping
            logging.info("I am sleeping")
            await asyncio.sleep(5)
        else:
            logging.info("Other status or error in get_am_i_here.") # if data is None or data[0] is not 0 or 1
            await asyncio.sleep(5)


async def back_home_task():
    pass


async def run_schedule():
    while True:
        schedule.run_pending()
        await asyncio.sleep(1)


async def main():
    args = parse_args()
    schedule.every().day.at("04:00", TIMEZONE).do(
        lambda: asyncio.create_task(
            morning_task(args.account, args.password, args.here_did, args.speaker_did)
        )
    )

    await run_schedule()


if __name__ == "__main__":
    logging.info("starting...")
    asyncio.run(main())
