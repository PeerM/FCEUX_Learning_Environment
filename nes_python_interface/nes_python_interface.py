# nes_python_interface.py
# Author: Ben Goodrich, Ehren J. Brav
# This partially implements a python version of the arcade learning
# environment interface.

from ctypes import *
import numpy as np
from numpy.ctypeslib import as_ctypes
import os
import typing

nes_lib = cdll.LoadLibrary(os.path.join(os.path.dirname(__file__), 'libfceux.so'))

nes_lib.NESInterface.argtypes = [c_char_p, c_bool]
nes_lib.NESInterface.restype = c_void_p

nes_lib.act.argtypes = [c_void_p, c_int]
nes_lib.act.restype = c_int

nes_lib.render.argtypes = [c_void_p]
nes_lib.render.restype = None

nes_lib.gameOver.argtypes = [c_void_p]
nes_lib.gameOver.restype = c_bool

nes_lib.resetGame.argtypes = [c_void_p]
nes_lib.resetGame.restype = None

nes_lib.getNumLegalActions.argtypes = [c_void_p]
nes_lib.getNumLegalActions.restype = c_int

nes_lib.getLegalActionSet.argtypes = [c_void_p, c_void_p]
nes_lib.getLegalActionSet.restype = None

nes_lib.getFrameNumber.argtypes = [c_void_p]
nes_lib.getFrameNumber.restype = c_int

nes_lib.lives.argtypes = [c_void_p]
nes_lib.lives.restype = c_int

nes_lib.getEpisodeFrameNumber.argtypes = [c_void_p]
nes_lib.getEpisodeFrameNumber.restype = c_int

nes_lib.getScreenHeight.argtypes = [c_void_p]
nes_lib.getScreenHeight.restype = c_int
nes_lib.getScreenWidth.argtypes = [c_void_p]
nes_lib.getScreenWidth.restype = c_int

nes_lib.getScreen.argtypes = [c_void_p, c_void_p, c_int]
nes_lib.getScreen.restype = None

nes_lib.fillRGBfromPalette.argtypes = [c_void_p, c_void_p, c_void_p, c_int]
nes_lib.fillRGBfromPalette.restype = None

nes_lib.getRam.argtypes = [c_void_p, c_void_p]
nes_lib.getRam.restype = None

nes_lib.saveState.argtypes = [c_void_p]
nes_lib.saveState.restype = None

nes_lib.loadState.argtypes = [c_void_p]
nes_lib.loadState.restype = c_bool

nes_lib.cloneState.argtypes = [c_void_p, c_void_p]
nes_lib.cloneState.restype = c_int

nes_lib.restoreState.argtypes = [c_void_p, c_void_p, c_int]
nes_lib.restoreState.restype = c_bool

nes_lib.delete_NES.argtypes = [c_void_p]
nes_lib.delete_NES.restype = None

nes_lib.getSnapshot.argtypes = [c_void_p, c_char_p]
nes_lib.getSnapshot.restype = None

nes_lib.restoreSnapshot.argtypes = [c_void_p, c_char_p]
nes_lib.restoreSnapshot.restype = None


class RewardTypes:
    ehrenbrav = "ehrenbrav"
    """use the C++ version from ehrenbrav """
    simple_function = "simple_function"
    """a pure function should be past alongside """
    factory = "factory"
    """a Factory that returns a stateful Callable should be past alongside"""


class NESInterface(object):
    def __init__(self, rom, eb_compatible=True, auto_render_period=-1,
                 reward_type=RewardTypes.ehrenbrav,
                 reward_function: typing.Callable = None,
                 reward_function_factory: typing.Callable = None):
        self.reward_type = reward_type
        if reward_type == RewardTypes.ehrenbrav:
            assert reward_function is None
            assert reward_function_factory is None
            self.reward_function = None
            self.reward_function_factory = None
        elif reward_type == RewardTypes.simple_function:
            assert reward_function is not None
            assert reward_function_factory is None
            self.reward_function = reward_function
            self.reward_function_factory = None
        elif reward_type == RewardTypes.factory:
            assert reward_function is None
            assert reward_function_factory is not None
            self.reward_function_factory = reward_function_factory
            self.reward_function = reward_function_factory()
        else:
            raise ValueError("unknown reward_type", reward_type)

        if eb_compatible and auto_render_period == -1:
            auto_render_period = 120
        self.should_render = auto_render_period != -1
        self.auto_render_period = auto_render_period
        self.render_action_counter = 0
        byte_string_rom = rom.encode('utf-8')
        self.obj = nes_lib.NESInterface(byte_string_rom, eb_compatible)
        self.width, self.height = self.getScreenDims()
        self.stateSize = None

    def act(self, action):
        reward = nes_lib.act(self.obj, int(action))
        if self.should_render:
            if self.render_action_counter % self.auto_render_period == 0:
                self.render()
                self.render_action_counter = 0
            self.render_action_counter += 1

        if self.reward_function is not None:
            return self.reward_function(self.getRAM())
        else:
            return reward

    def render(self):
        return nes_lib.render(self.obj)

    def game_over(self):
        return nes_lib.gameOver(self.obj)

    def reset_game(self):
        if self.reward_type == RewardTypes.factory:
            self.reward_function = self.reward_function_factory()
        nes_lib.resetGame(self.obj)

    def getLegalActionSet(self):
        act_size = nes_lib.getNumLegalActions(self.obj)
        act = np.zeros(shape=(act_size,), dtype=c_int)
        nes_lib.getLegalActionSet(self.obj, as_ctypes(act))
        return act

    def getMinimalActionSet(self):
        # For NES we assume this is the same
        # as the legal actions.

        # TODO Actually not true anymore but for now it works (yes, that old excuse ;))
        return self.getLegalActionSet()

    def getFrameNumber(self):
        return nes_lib.getFrameNumber(self.obj)

    def lives(self):
        return nes_lib.lives(self.obj)

    def getEpisodeFrameNumber(self):
        return nes_lib.getEpisodeFrameNumber(self.obj)

    def getScreenDims(self):
        """returns a tuple that contains (screen_width, screen_height)
        """
        width = nes_lib.getScreenWidth(self.obj)
        height = nes_lib.getScreenHeight(self.obj)
        return (width, height)

    def getScreen(self, screen_data=None):
        """This function fills screen_data with the RAW Pixel data
        screen_data MUST be a numpy array of uint8/int8. This could be initialized like so:
        screen_data = np.empty(w*h, dtype=np.uint8)
        Notice,  it must be width*height in size also
        If it is None,  then this function will initialize it
        Note: This is the raw pixel values,  before any RGB palette transformation takes place
        """
        if (screen_data is None):
            screen_data = np.zeros(self.width * self.height, dtype=np.uint8)

        nes_lib.getScreen(self.obj, as_ctypes(screen_data), c_int(screen_data.size))
        return screen_data

    def getScreenRGB(self, screen_data=None):
        """This function fills screen_data with the data in RGB format
        screen_data MUST be a numpy array of uint8. This can be initialized like so:
        screen_data = np.empty((height,width,3), dtype=np.uint8)
        If it is None,  then this function will initialize it.
        """
        if (screen_data is None):
            screen_data = np.empty((self.height, self.width, 1), dtype=np.uint8)

        # First get the raw screen.
        nes_lib.getScreen(self.obj, as_ctypes(screen_data), c_int(screen_data.size))

        # Now convert to RGB.
        rgb_screen = np.empty((self.height, self.width, 3), dtype=np.uint8)
        nes_lib.fillRGBfromPalette(self.obj, as_ctypes(screen_data), as_ctypes(rgb_screen), c_int(screen_data.size))
        return rgb_screen

    def getScreenGrayscale(self, screen_data=None):
        """This function fills screen_data with the data in grayscnes
        screen_data MUST be a numpy array of uint8. This can be initialized like so:
        screen_data = np.empty((height,width,1), dtype=np.uint8)
        If it is None,  then this function will initialize it.
        """
        if (screen_data is None):
            screen_data = np.empty((self.height, self.width, 1), dtype=np.uint8)
        nes_lib.getScreen(self.obj, as_ctypes(screen_data[:]), c_int(screen_data.size))
        return screen_data

    def getRAMSize(self):
        return 2048

    def getRAM(self, ram=None):
        """This function grabs the RAM.
        ram MUST be a numpy array of uint8/int8. This can be initialized like so:
        ram = np.array(ram_size, dtype=uint8)
        Notice: It must be ram_size where ram_size can be retrieved via the getRAMSize function.
        If it is None,  then this function will initialize it.
        """
        if (ram is None):
            ram_size = self.getRAMSize()
            ram = np.zeros(ram_size, dtype=np.uint8)
        nes_lib.getRam(self.obj, as_ctypes(ram))
        return ram

    def saveScreenPNG(self, filename):
        """Save the current screen as a png file"""
        return nes_lib.saveScreenPNG(self.obj, filename)

    def saveState(self):
        """Saves the state of the system"""
        return nes_lib.saveState(self.obj)

    def loadState(self):
        """Loads the state of the system"""
        return nes_lib.loadState(self.obj)

    def getSnapshot(self, snapshot_name):
        return nes_lib.getSnapshot(self.obj, snapshot_name)

    def restoreShapshot(self, snapshot_name):
        return nes_lib.restoreSnapshot(self.obj, snapshot_name)

    def cloneState(self, buffer=None):
        """This makes a copy of the environment state. This copy does *not*
        include pseudorandomness, making it suitable for planning
        purposes. By contrast, see cloneSystemState.
        """
        # hopefully this will not go wrong at some point or another
        external_buffer = buffer is not None
        if not external_buffer:
            buffer = np.empty(79304, np.uint8)
        used_size = nes_lib.cloneState(self.obj, as_ctypes(buffer))

        if not external_buffer:
            return buffer
        else:
            return used_size

    def restoreState(self, state):
        """state must be a numpy array with the right shape
        """
        size = state.shape[0]
        return nes_lib.restoreState(self.obj, as_ctypes(state), size)

    def cloneSystemState(self):
        """This makes a copy of the system & environment state, suitable for
        serialization. This includes pseudorandomness and so is *not*
        suitable for planning purposes.
        """
        return nes_lib.cloneSystemState(self.obj)

    def restoreSystemState(self, state):
        """Reverse operation of cloneSystemState."""
        nes_lib.restoreSystemState(self.obj, state)

    def deleteState(self, state):
        """ Deallocates the NESState """
        nes_lib.deleteState(state)

    def encodeStateLen(self, state):
        return nes_lib.encodeStateLen(state)

    def encodeState(self, state, buf=None):
        if buf == None:
            length = nes_lib.encodeStateLen(state)
            buf = np.zeros(length, dtype=np.uint8)
        nes_lib.encodeState(state, as_ctypes(buf), c_int(len(buf)))
        return buf

    def decodeState(self, serialized):
        return nes_lib.decodeState(as_ctypes(serialized), len(serialized))

    def __del__(self):
        nes_lib.delete_NES(self.obj)
