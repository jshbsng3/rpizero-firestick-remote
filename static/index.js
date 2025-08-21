
// Define appendToDisplay as empty to disable any appending for unmapped buttons
function appendToDisplay(value) {
    // Do nothing; leaves unmapped buttons inactive
}

// Function to send a command to the backend server
async function sendCommand(command) {
    try {
        const response = await fetch('/execute', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ command: command })
        });
        
        const result = await response.json();
        console.log('Command executed:', result);
        
        if (result.status !== 'success') {
            alert(`Error: ${result.error}`);
        }
    } catch (error) {
        console.error('Error executing command:', error);
        alert('Network error occurred.');
    }
}

// Add event listeners when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', () => {
    // Map only the specified buttons to their commands
    const buttonCommands = {
        'FireUp': 'UP',
        'FireLeft': 'LEFT',
        'FireSelect': 'ENTER',
        'FireRight': 'RIGHT',
        'FireDown': 'DOWN',
        'FireBack': 'ESC',
        'FireHome': 'HOME',
        'FireMenu': 'MENU',
        'FireRewind': 'REWIND',
        'FirePlayPause': 'PLAYPAUSE',
        'FireFastForward': 'FASTFORWARD',
        'FireReboot': 'FIREREBOOT',
        'RpiReboot': 'RPIREBOOT',
        'FireSleep': 'FIRESLEEP',
        'FireWake': 'FIREWAKE',
        'Plex': 'PLEX',
        'YouTube': 'YOUTUBE',
        'Prime': 'PRIME',
        'Netflix': 'NETFLIX',
        'Hulu': 'HULU',
        'HBO': 'HBO',
        'DiscoveryPlus': 'DISCOVERYPLUS',
        'ParamountPlus': 'PARAMOUNTPLUS',
        'AppleTV': 'APPLETV',
        
        'SoundbarOn': 'SOUNDBARON',
        'SoundbarInput': 'SOUNDBARINPUT',
        'SoundbarVolUp': 'SOUNDBARVOLUP',
        'SoundbarVolDown': 'SOUNDBARVOLDOWN',
        'SoundbarVolMute': 'SOUNDBARVOLMUTE',
        'SoundbarSubVolUp': 'SOUNDBARSUBVOLUP',
        'SoundbarSubVolDown': 'SOUNDBARSUBVOLDOWN',

        'TVPower': 'TVPOWER',
        'TVUp': 'TVUP',
        'TVInput': 'TVINPUT',
        'TVLeft': 'TVLEFT',
        'TVSelect': 'TVSELECT',
        'TVRight': 'TVRIGHT',
        'TVPBack': 'TVPBACK',
        'TVDown': 'TVDOWN',
        'TVMenu': 'TVMENU',
        'TVVolMute': 'TVVOLMUTE',
        'TVVolUp': 'TVVOLUP',
        'TVVolDown': 'TVVOLDOWN',

    };

    // Attach click event listeners only to mapped buttons
    Object.keys(buttonCommands).forEach(buttonId => {
        const button = document.getElementById(buttonId);
        if (button) {
            button.addEventListener('click', () => {
                sendCommand(buttonCommands[buttonId]);
            });
        } else {
            console.warn(`Button with ID ${buttonId} not found.`);
        }
    });

    // Handle the send button for the text input (wrap in quotes for string typing)
    const sendButton = document.getElementById('send-button');
    const commandInput = document.getElementById('command-input');

    if (sendButton && commandInput) {
        sendButton.addEventListener('click', () => {
            const text = commandInput.value.trim();
            if (text) {
                sendCommand(`"${text}"`);
                commandInput.value = ''; // Clear input after sending
            } else {
                console.warn('No text entered in the input field.');
            }
        });
    } else {
        console.warn('Send button or command input not found.');
    }
});