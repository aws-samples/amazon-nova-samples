import React, { createRef } from 'react';
import './eventDisplay.css'
import { Icon, Alert, Button, Modal, Box, SpaceBetween, Toggle, Container, Header, Badge, CodeEditor } from '@cloudscape-design/components';

class S2sEventDisplay extends React.Component {

    constructor(props) {
        super(props);
        this.state = {
            audioInputIndex: 0,
            eventsByContentName: [],

            selectedEvent: null,
            showEventJson: false,

            displayUsage: false,
        };
        this.message = null;
        this.reset = false;
    }

    componentDidUpdate(prevProps, prevState) {
        if (prevProps.message != this.props.message) {
            this.displayEvent(this.props.message);
        }
    }

    cleanup() {
        this.setState({
            eventsByContentName: [],
            audioInputIndex: 0,
            selectedEvent: null,
            showEventJson: false
        });
    }

    displayEvent(event, type) {
        if (event && event.event) {
            const eventName = Object.keys(event?.event)[0];
            let key = null;
            let ts = Date.now();
            let interrupted = false;
            const contentType = event.event[eventName].type;
            const contentName = event.event[eventName].contentName;
            const contentId = event.event[eventName].contentId;
            
            // Override type for tool-related events to display them on the left (as "out" events)
            if ((eventName === "contentStart" || eventName === "contentEnd") && contentType === "TOOL") {
                type = "out";
            }
            if (eventName === "textInput" && event.event[eventName].role === "TOOL") {
                type = "out";
            }
            if (eventName === "toolResult") {
                type = "out";
            }

            if (eventName === "audioOutput") {
                key = `${eventName}-${contentId}`;
                // truncate event audio content
                event.event.audioOutput.content = event.event.audioOutput.content.substr(0, 10);
            }
            else if (eventName === "audioInput") {
                key = `${eventName}-${contentName}-${this.state.audioInputIndex}`;
            }
            else if (eventName === "contentStart" || eventName === "textInput" || eventName === "contentEnd") {
                key = `${eventName}}-${contentName}-${contentType}`;
                if (type === "in" && event.event[eventName].type === "AUDIO") {
                    this.setState({ audioInputIndex: this.state.audioInputIndex + 1 });
                }
                else if (type === "out") {
                    key = `${eventName}-${contentName}-${contentType}-${ts}`;
                }
            }
            else if (eventName === "textOutput") {
                const role = event.event[eventName].role;
                const content = event.event[eventName].content;
                if (role === "ASSISTANT" && content.startsWith("{")) {
                    const evt = JSON.parse(content);
                    interrupted = evt.interrupted === true;
                }
                key = `${eventName}-${ts}`;
            }
            else {
                key = `${eventName}-${ts}`;
            }

            let eventsByContentName = this.state.eventsByContentName;
            if (eventsByContentName === null)
                eventsByContentName = [];

            let exists = false;
            for (var i = 0; i < eventsByContentName.length; i++) {
                var item = eventsByContentName[i];
                if (item.key === key && item.type === type) {
                    item.events.push(event);

                    item.interrupted = interrupted;
                    exists = true;
                    break;
                }
            }
            if (!exists) {
                const item = {
                    key: key,
                    name: eventName,
                    type: type,
                    events: [event],
                    ts: ts,
                };
                eventsByContentName.unshift(item);
            }

            // Limit audioInput and audioOutput events to 1000 to prevent memory issues
            if (eventName === "audioInput" || eventName === "audioOutput") {
                const audioEvents = eventsByContentName.filter(item => 
                    item.name === "audioInput" || item.name === "audioOutput"
                );
                
                if (audioEvents.length > 1000) {
                    // Remove oldest audio events, keeping only the most recent 1000
                    const audioEventsToRemove = audioEvents.slice(1000);
                    eventsByContentName = eventsByContentName.filter(item => 
                        !audioEventsToRemove.includes(item)
                    );
                }
            }

            this.setState({ eventsByContentName: eventsByContentName });
        }
    }

    render() {
        return (
            <div>
                <div className="toggleUsage">
                    <Toggle
                        onChange={({ detail }) =>
                            this.setState({ displayUsage: detail.checked })
                        }
                        checked={this.state.displayUsage}
                    >
                        Display Usage Event
                    </Toggle>
                </div>
                <div className='events'>
                    {this.state.eventsByContentName.map(event => {
                        if (!this.state.displayUsage && event.name === "usageEvent")
                            return;
                        else return <div className={
                            event.name === "toolUse" ? "event-tool-use" :
                                event.name === "toolResult" ? "event-tool-result" :
                                    event.name === "usageEvent" ? "event-usage" :
                                        event.interrupted === true ? "event-int" :
                                            event.type === "in" ? "event-in" : "event-out"
                            }
                            onClick={() => {
                                this.setState({ selectedEvent: event, showEventJson: true });
                            }}
                        >
                            <Icon name={event.type === "in" ? "arrow-down" : "arrow-up"} />&nbsp;&nbsp;
                            {event.name}
                            {event.events.length > 1 ? ` (${event.events.length})` : ""}
                            <div class="tooltip">
                                <pre id="jsonDisplay">{event.events.map(e => {
                                    return JSON.stringify(e, null, 2);
                                })
                                }</pre>
                            </div>
                        </div>
                    })}
                    <Modal
                        onDismiss={() => this.setState({ showEventJson: false })}
                        visible={this.state.showEventJson}
                        header={
                            <Header
                                variant="h1"
                                description={`Detailed view of ${this.state.selectedEvent?.name || 'event'} with ${this.state.selectedEvent?.events?.length || 0} occurrence(s)`}
                            >
                                Event Details
                            </Header>
                        }
                        size='large'
                        footer={
                            <Box float="right">
                                <SpaceBetween direction="horizontal" size="s">
                                    <Button variant="link" onClick={() => this.setState({ showEventJson: false })}>Close</Button>
                                    <Button 
                                        variant="primary" 
                                        onClick={() => {
                                            const eventData = this.state.selectedEvent?.events.map(e => {
                                                const eventType = Object.keys(e?.event)[0];
                                                if (eventType === "audioInput" || eventType === "audioOutput") {
                                                    const eventCopy = JSON.parse(JSON.stringify(e));
                                                    eventCopy.event[eventType].content = eventCopy.event[eventType].content.substr(0, 10) + "...";
                                                    return eventCopy;
                                                }
                                                return e;
                                            });
                                            navigator.clipboard.writeText(JSON.stringify(eventData, null, 2));
                                        }}
                                    >
                                        📋 Copy JSON
                                    </Button>
                                </SpaceBetween>
                            </Box>
                        }
                    >
                        <Container
                            header={
                                <Header
                                    variant="h2"
                                    actions={
                                        <SpaceBetween direction="horizontal" size="xs">
                                            <Badge color={this.state.selectedEvent?.type === 'in' ? 'green' : 'blue'}>
                                                {this.state.selectedEvent?.type === 'in' ? '⬇️ Incoming' : '⬆️ Outgoing'}
                                            </Badge>
                                            <Badge color="grey">
                                                {this.state.selectedEvent?.name}
                                            </Badge>
                                        </SpaceBetween>
                                    }
                                >
                                    Event Timeline
                                </Header>
                            }
                        >
                            <div className='event-detail-container'>
                                {this.state.selectedEvent && this.state.selectedEvent.events.map((e, index) => {
                                    const eventType = Object.keys(e?.event)[0];
                                    const eventCopy = JSON.parse(JSON.stringify(e));
                                    
                                    if (eventType === "audioInput" || eventType === "audioOutput") {
                                        eventCopy.event[eventType].content = eventCopy.event[eventType].content.substr(0, 10) + "...";
                                    }
                                    
                                    const ts = new Date(e.timestamp).toLocaleString(undefined, {
                                        year: "numeric",
                                        month: "2-digit",
                                        day: "2-digit",
                                        hour: "2-digit",
                                        minute: "2-digit",
                                        second: "2-digit",
                                        fractionalSecondDigits: 3,
                                        hour12: false
                                    });
                                    
                                    delete eventCopy.timestamp;
                                    
                                    return (
                                        <div key={index} className="event-item">
                                            <div className="event-timestamp">
                                                <Badge color="grey">🕒 {ts}</Badge>
                                            </div>
                                            <div className="event-json">
                                                <pre className="json-display">
                                                    {JSON.stringify(eventCopy, null, 2)}
                                                </pre>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </Container>
                    </Modal>
                </div>
            </div>
        );
    }
}

export default S2sEventDisplay;