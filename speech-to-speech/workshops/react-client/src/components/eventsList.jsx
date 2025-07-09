import { Icon, Button, Modal, Box, SpaceBetween } from '@cloudscape-design/components';
import React, { createRef } from 'react';
import './eventsList.css';

class EventDisplay extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            audioInputIndex: 0,
            eventsByContentName: [],

            selectedEvent: null,
            showEventJson: false,

            publicIpAddress: null,
            geolocation: null,
        };
        this.message = null;
        this.reset = false;
        this.eventsListEndRef = createRef(); // Reference for scrolling to the bottom
        this.eventsListRef = createRef(); // Reference to the events list container
    }

    componentDidMount() {
    }

    componentDidUpdate(prevProps, prevState) {
        if (prevProps.message !== this.props.message) {
            this.displayEvent(this.props.message);
        }
    }

    // Helper method to scroll to the bottom of events
    scrollToBottom = () => {
        if (this.eventsListEndRef.current) {
            requestAnimationFrame(() => {
                this.eventsListEndRef.current.scrollIntoView({
                    behavior: 'smooth',
                    block: 'end'
                });
            });
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
            if (eventsByContentName === null) {
                eventsByContentName = [];
            }

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
                eventsByContentName.push(item);

                this.scrollToBottom();
            }
            this.setState({ eventsByContentName: eventsByContentName });
        }
    }

    render() {
        return (
            <div className='events-list' ref={this.eventsListRef}>
                {this.state.eventsByContentName.map((event, index) => {
                    if (!this.props.showUsage && event.name === "usageEvent") {
                        return null;
                    } else return <div key={index} className={
                            event.name === "toolUse" ? "event-tool" :
                                event.name === "toolResult" ? "event-toolResult" :
                                    event.name === "usageEvent" ? "event-usage" :
                                        event.interrupted === true ? "event-int" :
                                            event.type === "in" ? "event-in" : "event-out"
                            }
                            onClick={() => {
                                this.setState({ selectedEvent: event, showEventJson: true });
                            }}
                        >

                        {event.type !== "in" ? <><Icon name="arrow-up" />&nbsp;&nbsp; </> : ""}

                        {event.name}
                        {event.events.length > 1 ? ` (${event.events.length})` : ""}

                        {event.type === "in" ?
                            event.name === "toolUse" ? <>&nbsp;&nbsp; <Icon name="arrow-right" /></> :
                                event.name === "toolResult" ? <>&nbsp;&nbsp; <Icon name="arrow-left" /></> :
                                <>&nbsp;&nbsp; <Icon name="arrow-down" /></> :
                                ""
                        }

                        <div className="tooltip">
                            <pre id="jsonDisplay">{event.events.map(e => {
                                return JSON.stringify(e, null, 2);
                            })
                            }</pre>
                        </div>
                    </div>
                })}
                {/* Reference element for scrolling to bottom */}
                <div ref={this.eventsListEndRef} className="events-end-marker"></div>

                <Modal
                    onDismiss={() => this.setState({ showEventJson: false })}
                    visible={this.state.showEventJson}
                    header="Event details"
                    size='medium'
                    footer={
                        <Box float="right">
                            <SpaceBetween direction="horizontal" size="xs">
                                <Button variant="link" onClick={() => this.setState({ showEventJson: false })}>Close</Button>
                            </SpaceBetween>
                        </Box>
                    }
                >
                    <div className='eventdetail'>
                        <pre id="jsonDisplay">
                            {this.state.selectedEvent && this.state.selectedEvent.events.map(e => {
                                const eventType = Object.keys(e?.event)[0];
                                if (eventType === "audioInput" || eventType === "audioOutput") {
                                    e.event[eventType].content = e.event[eventType].content.substr(0, 10) + "...";
                                }
                                const ts = new Date(e.timestamp).toISOString();
                                var displayJson = { ...e };
                                delete displayJson.timestamp;
                                return ts + "\n" + JSON.stringify(displayJson, null, 2) + "\n";
                            })}
                        </pre>
                    </div>
                </Modal>
            </div>
        );
    }
}

export default EventDisplay;
