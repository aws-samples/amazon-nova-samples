import React from 'react';
import { Icon, Button, Modal, Box, SpaceBetween, Link, ColumnLayout } from '@cloudscape-design/components';

class Meter extends React.Component {

    constructor(props) {
        super(props);
        this.state = {
            // Tokens
            totalInputSpeechToken: 0,
            totalInputTextToken: 0,
            totalOutputSpeechToken: 0,
            totalOutputTextToken: 0,

            // Cost
            totalInputSpeechCost: 0,
            totalInputTextCost: 0,
            totalOutputSpeechCost: 0,
            totalOutputTextCost: 0,

            showMeterDetail: false,

            startTime: null,
            elapsed: 0,
            elapsedDisplay: "0s",
        };
        // Sonic 2
        this.sonicPrice = {
            inputSpeech: 0.003,
            inputText: 0.00033,
            outputSpeech: 0.012,
            outputText: 0.00275
        };

        this.intervalId = null;
    }

    componentDidMount() {
        this.intervalId = setInterval(() => {
            if (this.state.startTime) {
                const elapsed = Date.now() - this.state.startTime;
                this.setState({
                    elapsed: elapsed,
                    elapsedDisplay: this.displayElapsed(elapsed)
                });
            }
        }, 500);
    }
    componentWillUnmount() {
        clearInterval(this.intervalId);
    }

    updateMeter(message) {
        if (message?.event?.usageEvent) {
            const usage = message.event.usageEvent;

            const input = usage.details?.total?.input;
            if (input) {
                input.speechTokens && this.setState({
                    totalInputSpeechToken: input.speechTokens,
                    totalInputSpeechCost: input.speechTokens / 1000 * this.sonicPrice.inputSpeech
                });
                input.textTokens && this.setState({
                    totalInputTextToken: input.textTokens,
                    totalInputTextCost: input.textTokens / 1000 * this.sonicPrice.inputText
                });
            }

            const output = usage.details?.total?.output;
            if (output) {
                output.speechTokens && this.setState({
                    totalOutputSpeechToken: output.speechTokens,
                    totalOutputSpeechCost: output.speechTokens / 1000 * this.sonicPrice.outputSpeech,
                });
                output.textTokens && this.setState({
                    totalOutputTextToken: output.textTokens,
                    totalOutputTextCost: output.textTokens / 1000 * this.sonicPrice.outputText
                });
            }
        }
    }

    formatCurrency(value, locale = 'en-US', currency = 'USD') {
        return new Intl.NumberFormat(locale, {
            style: 'currency',
            currency: currency,
        }).format(value);
    }

    start() {
        this.cleanup();
        this.setState({ startTime: new Date() });
    }

    stop() {
        this.setState({ startTime: null });
    }

    cleanup() {
        this.setState({
            totalInputSpeechToken: 0,
            totalInputTextToken: 0,
            totalOutputSpeechToken: 0,
            totalOutputTextToken: 0,

            // Cost
            totalInputSpeechCost: 0,
            totalInputTextCost: 0,
            totalOutputSpeechCost: 0,
            totalOutputTextCost: 0,

            startTime: null,
            elapsed: 0,
            elapsedDisplay: null,
        })
    }

    displayElapsed(elapsed) {
        if (elapsed > 0) {
            const hours = Math.floor(elapsed / (1000 * 60 * 60));
            elapsed %= (1000 * 60 * 60);

            const minutes = Math.floor(elapsed / (1000 * 60));
            elapsed %= (1000 * 60);

            const seconds = Math.floor(elapsed / 1000);
            const milliseconds = elapsed % 1000;

            let parts = [];

            if (hours > 0) parts.push(`${hours}h`);
            if (minutes > 0 || hours > 0) parts.push(`${minutes}m`); // show minutes if hours is shown

            parts.push(`${seconds}.${milliseconds}s`);

            return parts.join(' ');
        }
    }

    render() {
        const totalTokens = this.state.totalInputSpeechToken + this.state.totalInputTextToken + this.state.totalOutputSpeechToken + this.state.totalOutputTextToken;
        const totalCost = this.state.totalInputTextCost + this.state.totalInputSpeechCost + this.state.totalOutputTextCost + this.state.totalOutputSpeechCost;

        return (
            <div className="meter">
                <div
                    className="meter-content clickable"
                    onClick={() => this.setState({ showMeterDetail: true })}
                    title="Click to view detailed usage breakdown"
                >
                    <div className="meter-item">
                        <Icon name="clock" className="meter-icon" />
                        <span className="meter-label">Time:</span>
                        <span className="meter-value">{this.state.elapsedDisplay || '0s'}</span>
                    </div>
                    <div className="meter-divider">•</div>
                    <div className="meter-item">
                        <Icon name="gen-ai" className="meter-icon" />
                        <span className="meter-label">Tokens:</span>
                        <span className="meter-value">{totalTokens.toLocaleString()}</span>
                    </div>
                    <div className="meter-divider">•</div>
                    <div className="meter-item">
                        <Icon name="dollar" className="meter-icon" />
                        <span className="meter-label">Cost:</span>
                        <span className="meter-value">{this.formatCurrency(totalCost)}</span>
                    </div>
                    <div className="meter-expand-hint">
                        <Icon name="external" className="expand-icon" />
                    </div>
                </div>
                <Modal
                    onDismiss={() => this.setState({ showMeterDetail: false })}
                    visible={this.state.showMeterDetail}
                    header="📊 Session Usage Details"
                    size='large'
                    footer={
                        <div className='meter-modal-footer'>
                            <div className="pricing-info">
                                <h4>💰 Pricing per 1,000 tokens</h4>
                                <div className='pricing-grid'>
                                    <div className="pricing-item">
                                        <Icon name="microphone" /> Input Speech: <strong>${this.sonicPrice.inputSpeech}</strong>
                                    </div>
                                    <div className="pricing-item">
                                        <Icon name="edit" /> Input Text: <strong>${this.sonicPrice.inputText}</strong>
                                    </div>
                                    <div className="pricing-item">
                                        <Icon name="volume-up" /> Output Speech: <strong>${this.sonicPrice.outputSpeech}</strong>
                                    </div>
                                    <div className="pricing-item">
                                        <Icon name="file-text" /> Output Text: <strong>${this.sonicPrice.outputText}</strong>
                                    </div>
                                </div>
                            </div>
                            <Link
                                external
                                href="https://aws.amazon.com/bedrock/pricing/"
                                variant="primary"
                            >
                                View Amazon Bedrock Pricing
                            </Link>
                        </div>
                    }
                >
                    <div className='meter-modal-content'>
                        <div className="usage-summary">
                            <div className="summary-card total">
                                <Icon name="gen-ai" className="summary-icon" />
                                <div className="summary-info">
                                    <h3>Total Usage</h3>
                                    <div className="summary-value">{totalTokens.toLocaleString()} tokens</div>
                                    <div className="summary-cost">{this.formatCurrency(totalCost)}</div>
                                </div>
                            </div>
                        </div>

                        <div className="usage-breakdown">
                            <div className="breakdown-section">
                                <h4>📥 Input Usage</h4>
                                <div className="breakdown-grid">
                                    <div className="breakdown-item">
                                        <Icon name="microphone" />
                                        <div className="breakdown-info">
                                            <span className="breakdown-label">Speech Input</span>
                                            <span className="breakdown-tokens">{this.state.totalInputSpeechToken.toLocaleString()}</span>
                                            <span className="breakdown-cost">{this.formatCurrency(this.state.totalInputSpeechCost)}</span>
                                        </div>
                                    </div>
                                    <div className="breakdown-item">
                                        <Icon name="edit" />
                                        <div className="breakdown-info">
                                            <span className="breakdown-label">Text Input</span>
                                            <span className="breakdown-tokens">{this.state.totalInputTextToken.toLocaleString()}</span>
                                            <span className="breakdown-cost">{this.formatCurrency(this.state.totalInputTextCost)}</span>
                                        </div>
                                    </div>
                                </div>
                                <div className="section-total">
                                    Total Input: {(this.state.totalInputSpeechToken + this.state.totalInputTextToken).toLocaleString()} tokens
                                    ({this.formatCurrency(this.state.totalInputTextCost + this.state.totalInputSpeechCost)})
                                </div>
                            </div>

                            <div className="breakdown-section">
                                <h4>📤 Output Usage</h4>
                                <div className="breakdown-grid">
                                    <div className="breakdown-item">
                                        <Icon name="volume-up" />
                                        <div className="breakdown-info">
                                            <span className="breakdown-label">Speech Output</span>
                                            <span className="breakdown-tokens">{this.state.totalOutputSpeechToken.toLocaleString()}</span>
                                            <span className="breakdown-cost">{this.formatCurrency(this.state.totalOutputSpeechCost)}</span>
                                        </div>
                                    </div>
                                    <div className="breakdown-item">
                                        <Icon name="file-text" />
                                        <div className="breakdown-info">
                                            <span className="breakdown-label">Text Output</span>
                                            <span className="breakdown-tokens">{this.state.totalOutputTextToken.toLocaleString()}</span>
                                            <span className="breakdown-cost">{this.formatCurrency(this.state.totalOutputTextCost)}</span>
                                        </div>
                                    </div>
                                </div>
                                <div className="section-total">
                                    Total Output: {(this.state.totalOutputSpeechToken + this.state.totalOutputTextToken).toLocaleString()} tokens
                                    ({this.formatCurrency(this.state.totalOutputTextCost + this.state.totalOutputSpeechCost)})
                                </div>
                            </div>
                        </div>
                    </div>
                </Modal>

            </div>
        );
    }
}

export default Meter;