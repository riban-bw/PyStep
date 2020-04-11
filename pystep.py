#!/usr/bin/python3
import time
import tkinter as tk
import tkinter.font as tkFont
import threading
import jack
import json

# Global variables
displayWidth = 600
displayHeight = 400
clock = 0 # Count of MIDI clock pulses since last step [0..24]
status = "STOP" # Play status [STOP | PLAY]
playHead = 0 # Play head position in steps [0..gridColumns]
pattern = 0 # Index of current pattern
# List of notes in selected pattern, indexed by step: each step is list of events, each event is list of (note,velocity)
patterns = [] # List of patterns
trackHeight = 20 # Grid row height in pixels (default 20)
stepWidth = 40 # Grid column width in pixels (default 40)
gridRows = 16 # Quantity of rows in grid (default 16)
gridColumns = 16 # Quantity of columns in grid (default 16)
keyOrigin = 60 # MIDI note number of top row in grid
selectedCell = (0,0) # Location of selected cell (column,row)
inputVel = 100 # Velocity of new notes (default 100)
pianoRollWidth = 60 # Width of pianoroll in pixels (default 60)
titleCanvas = None

# Function to draw the play head cursor
def drawPlayhead():
    global playCanvas
    playCanvas.coords("playCursor", 1 + playHead * stepWidth, 0, playHead * stepWidth + stepWidth, trackHeight)

# Function to handle mouse click / touch
#   event: Mouse event
def onCanvasClick(event):
    closest = event.widget.find_closest(event.x, event.y)
    tags = gridCanvas.gettags(closest)
    toggleEvent(int(tags[0].split(',')[0]), [keyOrigin + int(tags[0].split(',')[1]), inputVel])

# Function to toggle note event
#   step: step (column) index
#   note: note list [note, velocity]
def toggleEvent(step, note):
    global selectedCell
    if step > gridRows or step > gridColumns:
        return
    found = False
    for event in patterns[pattern][step]:
        if event[0] == note[0]:
            patterns[pattern][step].remove(event)
            found = True
            break
    if not found:
        patterns[pattern][step].append(note)
    if note[0] >= keyOrigin and note[0] < keyOrigin + gridRows:
        selectCell(step, note[0] - keyOrigin)

# Function to draw a grid cell
#   step: Column index
#   note: Row index
def drawCell(col, row):
    if col > len(patterns[pattern]):
        return
    velocity = 255 # White
    for note in patterns[pattern][col]:
        if note[0] == keyOrigin + row:
            velocity = 255 - note[1] * 2
    fill = "#%02x%02x%02x" % (velocity, velocity, velocity)
    if selectedCell == (col, row):
        outline = '#00ff00'
    elif velocity == 0:
        outline = 'black'
    else:
        outline = '#dddddd'
    cell = gridCanvas.find_withtag("%d,%d"%(col,row))
    if cell:
        # Update existing cell
        gridCanvas.itemconfig(cell, fill=fill, outline=outline)
    else:
        # Create new cell
        cell = gridCanvas.create_rectangle(1 + col * stepWidth, (gridRows - row) * trackHeight, (col + 1) * stepWidth - 1, (gridRows - row - 1) * trackHeight + 1, fill=fill, outline=outline, tags=("%d,%d"%(col,row)))
        gridCanvas.tag_bind(cell, '<Button-1>', onCanvasClick)

# Function to draw grid
#   columns: Quantity of columns
#   rows: Quantity of rows
def drawGrid():
    # Delete existing note names
    for item in pianoRoll.find_withtag("notename"):
        pianoRoll.delete(item)
    # Draw cells of grid
    for row in range(gridRows):
        for col in range(gridColumns):
            drawCell(col, row)
        # Update pianoroll keys
        key = (keyOrigin + row) % 12
        if key in (0,2,4,5,7,9,11):
            pianoRoll.itemconfig(row + 1, fill="white")
            if key == 0:
                pianoRoll.create_text((pianoRollWidth / 2, trackHeight * (gridRows - row - 0.5)), text="C%d" % ((keyOrigin + row) // 12 - 1), tags="notename")
        else:
            pianoRoll.itemconfig(row + 1, fill="black")

# Function to send MIDI note on
#   note: List (MIDI note number, MIDI velocity)
#   NOTE: Which channel?
def noteOn(note):
    midiOutput.write_midi_event(0, (0x90, note[0], note[1]))

# Function to send MIDI note off
#   note: List (MIDI note number, MIDI velocity)
#   NOTE: Which channel?
def noteOff(note):
    midiOutput.write_midi_event(0, (0x80, note[0], note[1]))

# Function to handle JACK process events
#   frames: Quantity of frames since last process event
def onJackProcess(frames):
    global clock, status, playHead
    midiOutput.clear_buffer();
    for offset, data in midiInput.incoming_midi_events():
        if data[0] == b'\xf8':
            # MIDI Clock
            if status == "PLAY":
                clock = clock + 1
                if clock >= 24:
                    # Time to process a time slot
                    clock = 0
                    for note in patterns[pattern][playHead]:
                        noteOff(note)
                    playHead = playHead + 1
                    if playHead >= gridColumns:
                        playHead = 0
                    for note in patterns[pattern][playHead]:
                        noteOn(note)
                    drawPlayhead()
        elif data[0] == b'\xfa':
            # MIDI Start
            print("MIDI START")
            playHead = 0
            clock = 0
            status = "PLAY"
            drawPlayhead()
            playCanvas.itemconfig("playCursor", state = 'normal')
        elif data[0] == b'\xfb':
            # Midi Continue
            print("MIDI CONTINUE")
            status = "PLAY"
            playCanvas.itemconfig("playCursor", state = 'normal')
        elif data[0] == b'\xfc':
            # MIDI Stop
            print("MIDI STOP")
            status = "STOP"
            playCanvas.itemconfig("playCursor", state = 'hidden')
            for note in patterns[pattern][playHead]:
                noteOff(note)

# Function to draw pianoroll keys (does not fill key colour)
def drawPianoroll():
    for row in range(gridRows):
        y = trackHeight * (gridRows - row)
        item = pianoRoll.create_rectangle(0, y, pianoRollWidth, y - trackHeight)

# Function to update selectedCell
#   step: Step (column) of selected cell
#   note: Note number of selected cell
# NOTE: Removes previous selectedCell
def selectCell(col, row):
    global selectedCell, keyOrigin
    if col >= gridColumns or col < 0:
        return
    if row >= gridRows:
        if keyOrigin > 127 - gridRows:
            return
        keyOrigin = keyOrigin + 1
        drawGrid()
        return
    elif row < 0:
        if keyOrigin < 1:
            return
        keyOrigin = keyOrigin - 1
        drawGrid()
        return
    else:
        previousSelected = selectedCell
        selectedCell = (col, row)
        drawCell(previousSelected[0], previousSelected[1]) # Remove selection highlight
        drawCell(selectedCell[0], selectedCell[1])

# Function to save pattern to json file
def savePattern():
    with open('pattern.json', 'w') as f:
        json.dump(patterns, f)

# Function to handle keyboard key press event
#   event: Key event
def onKeyPress(event):
    global pattern
    if event.keycode == 98:
        #UP
        selectCell(selectedCell[0], selectedCell[1] + 1)
    elif event.keycode == 104:
        #DOWN
        selectCell(selectedCell[0], selectedCell[1] - 1)
    elif event.keycode == 100:
        #LEFT
        selectCell(selectedCell[0] - 1, selectedCell[1])
    elif event.keycode == 102:
        #RIGHT
        selectCell(selectedCell[0] + 1, selectedCell[1])
    elif event.keycode == 36:
        #ENTER
        toggleEvent(selectedCell[0], [keyOrigin + selectedCell[1], inputVel])
    elif event.keycode == 65:
        #SPACE
        pass
    elif event.keycode == 82:
        #- Select previous pattern
        loadPattern(pattern - 1)
    elif event.keycode == 86:
        #+ Select next pattern
        loadPattern(pattern + 1)
    elif event.keycode == 39:
        #S
        savePattern()
    else:
        print("Unhandled keypress code:", event.keycode)

# Function to load new pattern
def loadPattern(index):
    global pattern, gridColumns, gridCanvas, stepWidth, playHead
    if index >= len(patterns) or index < 0:
        return
    pattern = index
    gridColumns = len(patterns[pattern])
    if playHead >= gridColumns:
        playHead = 0
    stepWidth = displayWidth * 0.9 / gridColumns
    try:
        gridCanvas.destroy()
    except:
        pass # This will fail first time - don't worry
    gridCanvas = tk.Canvas(window, width=gridColumns * stepWidth, height=gridRows * trackHeight, bg="#eeeeee")
    gridCanvas.grid(row=1, column=1)
    drawGrid()
    playCanvas.config(width=gridColumns * stepWidth)
    titleCanvas.itemconfig("lblPattern", text="Pattern: %d" % pattern)

# Main application
if __name__ == "__main__":
    print("Starting PyStep...")
    # Load pattern from file
    try:
        with open('pattern.json') as f:
            patterns = json.load(f)
    except:
        print('Failed to load pattern file')
        patterns = [[[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[]]] # Default to 16 steps
    trackHeight = 0.9 * displayHeight/ (gridRows + 1)
    pianoRollWidth = displayWidth * 0.1
    # Create GUI
    window = tk.Tk()
    # Draw title bar
    titleCanvas = tk.Canvas(window, width=displayWidth, height=displayHeight * 0.1, bg="#70819e")
    titleCanvas.grid(row=0, column=0, columnspan=2)
    titleCanvas.create_text(2,2,text="Pattern: %d" % pattern, anchor="nw", font=tkFont.Font(family="Times Roman", size=20), tags="lblPattern")
    # Draw step grid
    pianoRoll = tk.Canvas(window, width=pianoRollWidth, height=gridRows * trackHeight, bg="white")
    pianoRoll.grid(row=1, column=0)
    drawPianoroll()
    # Draw playhead
    playCanvas = tk.Canvas(window, height=trackHeight, bg="#eeeeee")
    playCanvas.create_rectangle(0, 0, stepWidth, trackHeight, fill="green", state="hidden", tags="playCursor")
    playCanvas.grid(row=2, column=1)

    loadPattern(0) #TODO: Get last pattern from persistent storage
    window.bind("<Key>", onKeyPress)

    # Set up JACK interface
    jackClient = jack.Client("zynthstep")
    midiInput = jackClient.midi_inports.register("input")
    midiOutput = jackClient.midi_outports.register("output")
    jackClient.set_process_callback(onJackProcess)
    jackClient.activate()
    #TODO: Remove auto test connection 
    jackClient.connect("a2j:MidiSport 2x2 [20] (capture): MidiSport 2x2 MIDI 1", "zynthstep:input")
    jackClient.connect("zynthstep:output", "ZynMidiRouter:main_in")
    # Here we go....
    window.mainloop()
