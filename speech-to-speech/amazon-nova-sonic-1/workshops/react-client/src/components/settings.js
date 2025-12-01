import React from 'react';
import { Modal, Box, SpaceBetween, Button, FormField, Select, Textarea, Container, Header, ColumnLayout, Badge } from '@cloudscape-design/components';
import { VoicesByLanguage } from '../helper/config';

class Settings extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            configVoiceIdOption: props.configVoiceIdOption,
            configTurnSensitivity: props.configTurnSensitivity,
            configSystemPrompt: props.configSystemPrompt,
            configToolUse: props.configToolUse,
            configChatHistory: props.configChatHistory
        };
    }

    componentDidUpdate(prevProps) {
        // Update local state when props change
        if (prevProps.configVoiceIdOption !== this.props.configVoiceIdOption ||
            prevProps.configTurnSensitivity !== this.props.configTurnSensitivity ||
            prevProps.configSystemPrompt !== this.props.configSystemPrompt ||
            prevProps.configToolUse !== this.props.configToolUse ||
            prevProps.configChatHistory !== this.props.configChatHistory) {
            this.setState({
                configVoiceIdOption: this.props.configVoiceIdOption,
                configTurnSensitivity: this.props.configTurnSensitivity,
                configSystemPrompt: this.props.configSystemPrompt,
                configToolUse: this.props.configToolUse,
                configChatHistory: this.props.configChatHistory
            });
        }
    }

    handleVoiceIdChange = ({ detail }) => {
        // Find the full voice data from the config
        let fullVoiceData = null;
        Object.values(VoicesByLanguage).forEach(langData => {
            const voice = langData.voices.find(v => v.value === detail.selectedOption.value);
            if (voice) {
                fullVoiceData = {
                    label: `${voice.label} (${voice.accent})`,
                    value: voice.value,
                    ...voice
                };
            }
        });

        const voiceOption = fullVoiceData || detail.selectedOption;
        this.setState({ configVoiceIdOption: voiceOption });
        if (this.props.onSettingsChange) {
            this.props.onSettingsChange({ configVoiceIdOption: voiceOption });
        }
    }

    handleTurnSensitivityChange = (e) => {
        this.setState({ configTurnSensitivity: e.target.value });
        if (this.props.onSettingsChange) {
            this.props.onSettingsChange({ configTurnSensitivity: e.target.value });
        }
    }

    handleSystemPromptChange = ({ detail }) => {
        this.setState({ configSystemPrompt: detail.value });
        if (this.props.onSettingsChange) {
            this.props.onSettingsChange({ configSystemPrompt: detail.value });
        }
    }

    handleToolUseChange = ({ detail }) => {
        this.setState({ configToolUse: detail.value });
        if (this.props.onSettingsChange) {
            this.props.onSettingsChange({ configToolUse: detail.value });
        }
    }

    handleChatHistoryChange = ({ detail }) => {
        this.setState({ configChatHistory: detail.value });
        if (this.props.onSettingsChange) {
            this.props.onSettingsChange({ configChatHistory: detail.value });
        }
    }

    getGroupedVoiceOptions = () => {
        return Object.entries(VoicesByLanguage).map(([language, langData]) => ({
            label: `${langData.flag} ${language}`,
            options: langData.voices.map(voice => ({
                label: `${voice.label} (${voice.gender}, ${voice.accent})`,
                value: voice.value,
            }))
        }));
    }

    render() {
        const { visible, onDismiss } = this.props;

        return (
            <Modal
                onDismiss={onDismiss}
                visible={visible}
                header={
                    <Header
                        variant="h1"
                        description="Configure your Nova Sonic conversation settings"
                    >
                        Nova Sonic Settings
                    </Header>
                }
                size='large'
                footer={
                    <Box float="right">
                        <SpaceBetween direction="horizontal" size="s">
                            <Button variant="link" onClick={onDismiss}>Cancel</Button>
                            <Button variant="primary" onClick={onDismiss}>Save Settings</Button>
                        </SpaceBetween>
                    </Box>
                }
            >
                <SpaceBetween size="l">
                    {/* Voice & Conversation Settings */}
                    <Container
                        header={
                            <Header variant="h2">
                                Voice & Conversation
                            </Header>
                        }
                    >
                        <ColumnLayout columns={2} variant="text-grid">
                            <FormField
                                label={
                                    <SpaceBetween direction="horizontal" size="xs">
                                        <span>Voice Selection</span>
                                        <Badge color="blue">Audio</Badge>
                                    </SpaceBetween>
                                }
                                description="Choose the voice for AI responses, organized by language"
                                stretch={true}
                            >
                                <Select
                                    selectedOption={this.state.configVoiceIdOption}
                                    onChange={this.handleVoiceIdChange}
                                    options={this.getGroupedVoiceOptions()}
                                    placeholder="Select a voice"
                                    filteringType="auto"
                                    expandToViewport={true}
                                />
                            </FormField>

                            {false && <FormField
                                label={
                                    <SpaceBetween direction="horizontal" size="xs">
                                        <span>Turn Sensitivity</span>
                                        <Badge color="green">Timing</Badge>
                                    </SpaceBetween>
                                }
                                description="How quickly the AI responds to pauses"
                                stretch={true}
                            >
                                <div className="turn-sensitivity-options-enhanced">
                                    <label className="radio-option-enhanced">
                                        <input
                                            type="radio"
                                            name="turnSensitivity"
                                            value="HIGH"
                                            checked={this.state.configTurnSensitivity === "HIGH"}
                                            onChange={this.handleTurnSensitivityChange}
                                        />
                                        <span className="radio-label">
                                            <strong>High</strong>
                                        </span>
                                    </label>
                                    <label className="radio-option-enhanced">
                                        <input
                                            type="radio"
                                            name="turnSensitivity"
                                            value="MEDIUM"
                                            checked={this.state.configTurnSensitivity === "MEDIUM"}
                                            onChange={this.handleTurnSensitivityChange}
                                        />
                                        <span className="radio-label">
                                            <strong>Medium</strong>
                                        </span>
                                    </label>
                                    <label className="radio-option-enhanced">
                                        <input
                                            type="radio"
                                            name="turnSensitivity"
                                            value="LOW"
                                            checked={this.state.configTurnSensitivity === "LOW"}
                                            onChange={this.handleTurnSensitivityChange}
                                        />
                                        <span className="radio-label">
                                            <strong>Low</strong>
                                        </span>
                                    </label>
                                </div>
                            </FormField>}
                        </ColumnLayout>
                    </Container>

                    {/* AI Behavior Settings */}
                    <Container
                        header={
                            <Header variant="h2">
                                AI Behavior
                            </Header>
                        }
                    >
                        <FormField
                            label={
                                <SpaceBetween direction="horizontal" size="xs">
                                    <span>System Prompt</span>
                                    <Badge color="purple">Personality</Badge>
                                </SpaceBetween>
                            }
                            description="Define how the AI should behave and respond during conversations"
                            stretch={true}
                        >
                            <Textarea
                                onChange={this.handleSystemPromptChange}
                                value={this.state.configSystemPrompt}
                                placeholder="Enter system prompt to define AI behavior..."
                                rows={6}
                                resize="vertical"
                            />
                        </FormField>
                    </Container>

                    {/* Advanced Configuration */}
                    <Container
                        header={
                            <Header 
                                variant="h2"
                                description="Advanced settings for developers and power users"
                            >
                                Advanced Configuration
                            </Header>
                        }
                    >
                        <SpaceBetween size="m">
                            <FormField
                                label={
                                    <SpaceBetween direction="horizontal" size="xs">
                                        <span>Tool Configuration</span>
                                        <Badge color="red">JSON</Badge>
                                    </SpaceBetween>
                                }
                                description="Configure external tools and integrations (RAG, Agents, APIs)"
                                stretch={true}
                            >
                                <Textarea
                                    onChange={this.handleToolUseChange}
                                    value={this.state.configToolUse}
                                    rows={8}
                                    placeholder='{"tools": []}'
                                    resize="vertical"
                                />
                            </FormField>

                            <FormField
                                label={
                                    <SpaceBetween direction="horizontal" size="xs">
                                        <span>Chat History</span>
                                        <Badge color="grey">Context</Badge>
                                    </SpaceBetween>
                                }
                                description="Sample conversation history to provide context for the AI"
                                stretch={true}
                            >
                                <Textarea
                                    onChange={this.handleChatHistoryChange}
                                    value={this.state.configChatHistory}
                                    rows={10}
                                    placeholder='[{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi there!"}]'
                                    resize="vertical"
                                />
                            </FormField>
                        </SpaceBetween>
                    </Container>
                </SpaceBetween>
            </Modal>
        );
    }
}

export default Settings;