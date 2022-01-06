import sys
import os
import threading
from queue import Queue, Full

import logging
from time import time, sleep
import json

from typing import List

from exceptions import RuntimeError


_LOGGER = logging.getLogger('mme')


def modules_organized_by_name(modules: List[dict]) -> dict:
    modules_by_names = {}
    for module in modules:
        modules_by_names[module.get('name')] = module
    return modules_by_names

def modules_organized_by_id(modules: List[dict]) -> dict:
    modules_by_id = {}
    for module in modules:
        modules_by_id[module.get('arbitration_id')] = module
    return modules_by_id

def load_modules(file: str) -> dict:
    with open(file) as infile:
        modules = json.load(infile)
    return modules

def get_module_name(arbitration_id: int) -> str:
    return modules_by_id.get(arbitration_id, '???')


modules = load_modules(file='json/mme_modules.json')
modules_by_name = modules_organized_by_name(modules)
modules_by_id = modules_organized_by_id(modules)


class PlaybackEngine:

    def __init__(self, config: dict, queues: dict) -> None:
        self._config = config
        self._queues = queues
        self._playback_files = self._get_playback_files(config.get('source_dir'), config.get('source_file'))
        self._start_at = config.get('start_at', 0)
        self._speed = config.get('speed', 1)
        self._exit_requested = False
        self._time_zero = int(time())
        self._currrent_position = None
        self._current_playback = None

    def _get_playback_files(self, source_dir: str, source_file: str) -> List:
        playback_files = []
        count = 0
        find_file = f"{source_dir}/{source_file}_{count:03d}.json"
        while True:
            if not os.path.exists(find_file):
                break
            playback_files.append(find_file)
            count += 1
            find_file = f"{source_dir}/{source_file}_{count:03d}.json"
        return playback_files

    def start(self) -> None:
        self._exit_requested = False
        """
        if self._start_at > 0:
            offset = 0
            for event in self._playback:
                if event.get('time') < self._start_at:
                    offset += 1
                    continue
                break
            self._currrent_playback = offset
            self._time_zero -= event.get('time')
        """
        self._thread = threading.Thread(target=self._event_task, name='playback')
        self._thread.start()
        self._thread.join()

    def _event_task(self) -> None:
        try:
            while self._exit_requested == False:
                event = self._next_event()
                if event is None:
                    return
                current_time = round(time() - self._time_zero, ndigits=2)
                event_time = event.get('time')
                if current_time < event_time:
                    sleep_for = event_time - current_time
                    if sleep_for > 0:
                        if sleep_for > 5:
                            print(f"sleeping for {sleep_for} seconds")
                        sleep(sleep_for)
                current_time = round(time() - self._time_zero, ndigits=2)
                arbitration_id = event.get('id')
                name = modules_by_id.get(arbitration_id).get('name')
                destination = self._queues.get(name)
                if destination:
                    try:
                        destination.put(event, block=False, timeout=2)
                        #print(f"{current_time:.02f}: {self._decode_event(event)}")
                    except Full:
                        _LOGGER.error(f"Queue {arbitration_id:04X} is full")
        except RuntimeError as e:
            _LOGGER.error(f"Run time error: {e}")
            return

    def stop(self) -> None:
        self._exit_requested = True
        if self._thread.is_alive():
            self._thread.join()

    def _next_event(self) -> dict:
        if self._currrent_position is None or self._currrent_position == len(self._current_playback):
            if self._playback_files == []:
                return
            next_file = self._playback_files.pop(0)
            self._load_playback(file=next_file)
        event = self._current_playback[self._currrent_position]
        self._currrent_position += 1
        return event

    def _decode_event(self, event: dict) -> str:
        module_name = get_module_name(event.get('id')).get('name')
        event['id'] = module_name
        event['payload'] = bytearray(event['payload'])
        return str(event)

    def _load_playback(self, file: str) -> None:
        with open(file) as infile:
            try:
                self._current_playback = json.load(infile)
                _LOGGER.info(f"Loaded playback file '{file}'")
            except json.JSONDecodeError as e:
                raise RuntimeError(f"JSON error in '{file}' at line {e.lineno}")
        self._currrent_position = 0                

    def _dump_playback(self, file: str, playback: dict) -> None:
        json_playback = json.dumps(playback, indent = 4, sort_keys=False)
        with open(file, "w") as outfile:
            outfile.write(json_playback)


def main() -> None:
    queues = {}
    for module in modules:
        arbitration_id = module.get('arbitration_id')
        q = Queue(maxsize=10)
        queues[arbitration_id] = q

    pb = PlaybackEngine(file='playback.json', queues=queues)
    try:
        pb.start()
        while True:
            try:
                for arbitration_id, queue in queues.items():
                    while queue.empty() == False:
                        event = queue.get(block='False')
                        print(f"{event}")
                sleep(0.25)
            except KeyboardInterrupt:
                break
    except Exception as e:
        print(f"Unexpected exception: {e}")
    finally:
        pb.stop()


if __name__ == '__main__':
    if sys.version_info[0] >= 3 and sys.version_info[1] >= 10:
        main()
    else:
        print("python 3.10 or better required")
