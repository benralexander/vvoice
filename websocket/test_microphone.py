#!/usr/bin/env python3

import json
import os
import sys
import asyncio
import websockets
import logging
import sounddevice as sd
import argparse
from pynput.keyboard import Controller, Key

def int_or_str(text):
    """Helper function for argument parsing."""
    try:
        return int(text)
    except ValueError:
        return text

keyboard = Controller()

def send_output(text:str,out_form:str):
    if out_form=='k':
        keyboard.type(text)
    else:
        print(text)

def callback(indata, frames, time, status):
    """This is called (from a separate thread) for each audio block."""
    loop.call_soon_threadsafe(audio_queue.put_nowait, bytes(indata))

async def run_test(out_form:str):

    with sd.RawInputStream(samplerate=args.samplerate, blocksize = 4000, device=args.device, dtype='int16',
                           channels=1, callback=callback) as device:

        async with websockets.connect(args.uri) as websocket:
            await websocket.send('{ "config" : { "sample_rate" : %d } }' % (device.samplerate))

            while True:
                data = await audio_queue.get()
                await websocket.send(data)
                json_rep = (await websocket.recv())
                decoded_json = json.loads(json_rep)

                if len(decoded_json.get("result","")):
                    res=decoded_json.get("result")
                    words=[x.get("word","") for x in res if len(x.get("word","")) ]
                    if len(words)>0 and words[0]=="the":
                        words.pop(0)
                    string_to_output= ' '.join(words)
                    send_output(string_to_output,out_form)
                    if string_to_output=="go to sleep":
                        sys.exit(0)



            await websocket.send('{"eof" : 1}')

async def main():

    global args
    global loop
    global audio_queue

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('-l', '--list-devices', action='store_true',
                        help='show list of audio devices and exit')
    args, remaining = parser.parse_known_args()
    if args.list_devices:
        print(sd.query_devices())
        parser.exit(0)
    parser = argparse.ArgumentParser(description="ASR Server",
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     parents=[parser])
    parser.add_argument('-u', '--uri', type=str, metavar='URL',
                        help='Server URL', default='ws://localhost:2700')
    parser.add_argument('-d', '--device', type=int_or_str,
                        help='input device (numeric ID or substring)')
    parser.add_argument('-r', '--samplerate', type=int, help='sampling rate', default=16000)
    parser.add_argument('-o', '--output', type=int_or_str,
                        help='print (p) result or simulate keyboard (k)',default='p')
    args = parser.parse_args(remaining)
    loop = asyncio.get_running_loop()
    audio_queue = asyncio.Queue()


    logging.basicConfig(level=logging.INFO)

    await run_test(args.output)

if __name__ == '__main__':
    asyncio.run(main())
