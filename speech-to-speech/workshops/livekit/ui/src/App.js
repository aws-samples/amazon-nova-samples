import React from 'react';
import { LiveKitRoom, AudioConference } from '@livekit/components-react';
import '@livekit/components-styles';
import './App.css';

const TOKEN = process.env.REACT_APP_LIVEKIT_TOKEN;
const WS_URL = process.env.REACT_APP_LIVEKIT_SERVER_URL?process.env.REACT_APP_LIVEKIT_SERVER_URL:"ws://localhost:7880";

class App extends React.Component {

    constructor(props) {
        super(props);
        this.state = {};
    }

    render() {
        return (
          <div className='livekit'>
            <div className='title'>Chat with Nova Sonic via LiveKit</div>
            <div className='url'>{WS_URL}</div>
              <div data-lk-theme="default" >
                <LiveKitRoom audio={true} video={false} token={TOKEN} serverUrl={WS_URL} connect={true}>
                  <AudioConference />
                </LiveKitRoom>
              </div>
          </div>
        );
    }
}

export default App;