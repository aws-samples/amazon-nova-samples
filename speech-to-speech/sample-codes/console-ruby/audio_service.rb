# frozen_string_literal: true

require 'aws-sdk-bedrockruntime'
require 'securerandom'
require 'json'
require 'base64'
require 'concurrent'

module NovaSonic
  class AudioService
    attr_reader :session_id, :logger

    class << self
      def active_sessions
        @active_sessions ||= {}
      end

      def session_cleanup_in_progress
        @session_cleanup_in_progress ||= Set.new
      end

      def cleanup_in_progress?(session_id)
        session_cleanup_in_progress.include?(session_id)
      end

      def session_creation_mutexes
        @session_creation_mutexes ||= {}
      end
    end

    def initialize(session_id, logger = Rails.logger)
      @session_id = session_id
      @logger = logger

      @inference_config = {
        maxTokens: 10_000,
        topP: 0.95,
        temperature: 0.9
      }

      initialize_aws_client
    end

    def setup_session
      create_stream_session
      initiate_session
      @logger.info "Session setup completed successfully for #{session_id}"
      self
    rescue StandardError => e
      @logger.error "Error in setup_session: #{e.message}"
      @logger.error "Backtrace: #{e.backtrace.first(3).join('; ')}"
      raise e
    end

    def stop_audio_streaming
      session_data = self.class.active_sessions[session_id]
      return unless session_data

      begin
        send_content_end if session_data[:input_stream]

        session_data[:is_audio_content_start_sent] = false
        session_data[:audio_content_id] = SecureRandom.uuid

        @logger.info "Audio streaming stopped for session #{session_id}, session remains active"
      rescue StandardError => e
        @logger.error "Error stopping audio streaming: #{e.message}"
      end
    end

    def close_session
      session_data = self.class.active_sessions[session_id]
      return unless session_data

      self.class.session_cleanup_in_progress << session_id

      begin
        send_content_end if session_data[:input_stream]
        send_prompt_end if session_data[:input_stream]
        send_session_end if session_data[:input_stream]
      rescue StandardError => e
        @logger.error "Error closing AWS streams: #{e.message}"
      end

      self.class.active_sessions.delete(session_id)
      self.class.session_creation_mutexes.delete(session_id)
      self.class.session_cleanup_in_progress.delete(session_id)

      @logger.info "Session #{session_id} closed and cleaned up"
    end

    def stream_audio(audio_data)
      decoded_audio = Base64.decode64(audio_data)
      stream_audio_data(decoded_audio)
    end

    def stream_audio_data(audio_data)
      return if audio_data.nil? || audio_data.empty?

      session_data = self.class.active_sessions[session_id]
      unless session_data&.[](:is_active)
        @logger.error "Session #{session_id} not found or inactive"
        return
      end

      @logger.debug "Streaming audio data: #{audio_data.length} bytes"

      if !session_data[:is_audio_content_start_sent] && session_data[:input_stream].present?
        @logger.debug "Sending audio content start"
        send_audio_content_start
        session_data[:is_audio_content_start_sent] = true
      end

      stream_audio_chunk(audio_data)
    end

    def setup_system_prompt(content)
      return false if content.blank?

      @custom_system_prompt = content
      @logger.info "Custom system prompt stored for session #{session_id}"
      true
    end

    def on_event(event_type, &handler)
      @event_handlers ||= {}
      @event_handlers[event_type] = handler
      self
    end

    private

    def initialize_aws_client
      client_options = {
        region: 'us-east-1',
        http_wire_trace: false,
        enable_alpn: true
      }

      @bedrock_runtime_client = Aws::BedrockRuntime::AsyncClient.new(client_options)
    end

    def create_stream_session
      session_mutex = self.class.session_creation_mutexes[session_id] ||= Mutex.new

      session_mutex.synchronize do
        return if self.class.active_sessions[session_id]

        session_data = {
          queue_mutex: Mutex.new,
          prompt_name: SecureRandom.uuid,
          inference_config: @inference_config,
          is_active: true,
          is_prompt_start_sent: false,
          is_audio_content_start_sent: false,
          audio_content_id: SecureRandom.uuid
        }

        self.class.active_sessions[session_id] = session_data
      end
    end

    def initiate_session
      session_data = self.class.active_sessions[session_id]
      unless session_data
        @logger.error "Stream session #{session_id} not found in active_sessions"
        raise "Stream session #{session_id} not found"
      end

      session_data[:queue_mutex].synchronize do
        return if session_data[:initializing]
        return if session_data[:is_active] && session_data[:input_stream]

        session_data[:initializing] = true
      end

      begin
        initialize_session_core(session_data)
        @logger.info "Session #{session_id} initialization completed successfully"
      rescue StandardError => e
        @logger.error "Session #{session_id} initialization failed: #{e.class} - #{e.message}"
        handle_initialization_error(e)

        raise e
      ensure
        session_data[:initializing] = false
      end
    end

    def initialize_session_core(session_data)
      input_stream = Aws::BedrockRuntime::EventStreams::InvokeModelWithBidirectionalStreamInput.new
      output_stream = Aws::BedrockRuntime::EventStreams::InvokeModelWithBidirectionalStreamOutput.new

      setup_output_stream_handlers(output_stream)

      prompt_id = SecureRandom.uuid
      text_content_id = SecureRandom.uuid
      audio_content_id = SecureRandom.uuid

      session_data[:prompt_name] = prompt_id
      session_data[:audio_content_id] = audio_content_id

      async_resp = @bedrock_runtime_client.invoke_model_with_bidirectional_stream(
        model_id: 'amazon.nova-sonic-v1:0',
        input_event_stream_handler: input_stream,
        output_event_stream_handler: output_stream
      )

      session_data[:input_stream] = input_stream
      session_data[:async_resp] = async_resp

      send_initial_events(input_stream, prompt_id, text_content_id, session_data[:audio_content_id])

      session_data[:is_active] = true
      session_data[:is_prompt_start_sent] = true
      session_data[:is_audio_content_start_sent] = true
    end

    def setup_output_stream_handlers(output_stream)
      output_stream.on_event do |event|
        handle_aws_event(event)
      rescue StandardError => e
        @logger.error "Error handling AWS event: #{e.message}"
      end
    end

    def handle_aws_event(event)
      if event.is_a?(Hash) && event[:event_type] == :chunk && event[:bytes]
        begin
          response_data = JSON.parse(event[:bytes])

          if response_data['event']
            event_type = response_data['event'].keys.first
            event_data = response_data['event'][event_type]

            dispatch_event(event_type, event_data)
          end
        rescue JSON::ParserError => e
          @logger.error "Failed to parse JSON response: #{e.message}"
        end
      elsif event.respond_to?(:event_type) && event.event_type == :chunk && event.respond_to?(:bytes)
        begin
          response_data = JSON.parse(event.bytes)

          if response_data['event']
            event_type = response_data['event'].keys.first
            event_data = response_data['event'][event_type]

            dispatch_event(event_type, event_data)
          end
        rescue JSON::ParserError => e
          @logger.error "Failed to parse JSON response: #{e.message}"
        end
      end
    end

    def dispatch_event(event_type, data)
      @logger.debug "Dispatching event: #{event_type}"
      @event_handlers[event_type]&.call(data)

      return unless @event_handlers&.[]('any')

      @event_handlers['any'].call({ type: event_type, data: })
    end

    def send_initial_events(input_stream, prompt_id, text_content_id, audio_content_id)
      events = build_initial_events(prompt_id, text_content_id, audio_content_id)
      send_events_to_stream(input_stream, events)
    end

    def build_initial_events(prompt_id, text_content_id, audio_content_id)
      system_prompt = @custom_system_prompt || default_system_prompt

      [
        build_session_start_event,
        build_prompt_start_event(prompt_id),
        build_text_content_start_event(prompt_id, text_content_id),
        build_system_prompt_event(prompt_id, text_content_id, system_prompt),
        build_text_content_end_event(prompt_id, text_content_id),
        build_audio_content_start_event(prompt_id, audio_content_id)
      ]
    end

    def send_events_to_stream(input_stream, events)
      events.each_with_index do |event, index|
        input_stream.signal_chunk_event(bytes: event)
      rescue StandardError => e
        @logger.error "Error sending initial event #{index + 1}: #{e.message}"
        raise "Failed to send initial event: #{e.message}"
      end
    end

    def build_session_start_event
      {
        event: {
          sessionStart: {
            inferenceConfiguration: @inference_config
          }
        }
      }.to_json
    end

    def build_prompt_start_event(prompt_id)
      {
        event: {
          promptStart: {
            promptName: prompt_id,
            textOutputConfiguration: {
              mediaType: 'text/plain'
            },
            audioOutputConfiguration: {
              mediaType: 'audio/lpcm',
              sampleRateHertz: 16_000,
              sampleSizeBits: 16,
              channelCount: 1,
              voiceId: 'en_us_tiffany',
              encoding: 'base64',
              audioType: 'SPEECH'
            },
            toolUseOutputConfiguration: {
              mediaType: 'application/json'
            },
            toolConfiguration: {
              tools: []
            }
          }
        }
      }.to_json
    end

    def build_text_content_start_event(prompt_id, text_content_id)
      {
        event: {
          contentStart: {
            promptName: prompt_id,
            contentName: text_content_id,
            type: 'TEXT',
            interactive: true,
            textInputConfiguration: {
              mediaType: 'text/plain'
            }
          }
        }
      }.to_json
    end

    def build_system_prompt_event(prompt_id, text_content_id, system_prompt)
      {
        event: {
          textInput: {
            promptName: prompt_id,
            contentName: text_content_id,
            content: system_prompt,
            role: 'SYSTEM'
          }
        }
      }.to_json
    end

    def build_text_content_end_event(prompt_id, text_content_id)
      {
        event: {
          contentEnd: {
            promptName: prompt_id,
            contentName: text_content_id
          }
        }
      }.to_json
    end

    def build_audio_content_start_event(prompt_id, audio_content_id)
      {
        event: {
          contentStart: {
            promptName: prompt_id,
            contentName: audio_content_id,
            type: 'AUDIO',
            role: 'USER',
            interactive: true,
            audioInputConfiguration: {
              mediaType: 'audio/lpcm',
              sampleRateHertz: 16_000,
              sampleSizeBits: 16,
              channelCount: 1,
              audioType: 'SPEECH',
              encoding: 'base64'
            }
          }
        }
      }.to_json
    end

    def stream_audio_chunk(audio_data)
      session_data = self.class.active_sessions[session_id]

      unless session_data&.[](:is_active)
        @logger.error "Session #{session_id} not found or inactive"
        @logger.error "Available sessions: #{self.class.active_sessions.keys}"
        raise "Session not active or not found: #{session_id}"
      end

      unless session_data[:input_stream]
        @logger.error "No input stream available for session #{session_id}"
        raise "No input stream available for session: #{session_id}"
      end

      if audio_data.nil? || audio_data.empty?
        @logger.error "Empty audio data received for session #{session_id}"
        raise 'Empty audio data received'
      end

      base64_data = Base64.strict_encode64(audio_data)

      audio_event = {
        event: {
          audioInput: {
            promptName: session_data[:prompt_name],
            contentName: session_data[:audio_content_id],
            content: base64_data,
            role: 'USER'
          }
        }
      }.to_json

      begin
        session_data[:input_stream].signal_chunk_event(bytes: audio_event)
      rescue StandardError => e
        @logger.error "Failed to send audio chunk: #{e.message}"
        session_data[:is_active] = false
        session_data[:input_stream] = nil
        raise e
      end
    end

    def default_system_prompt
      'You are a friendly assistant. The user and you will engage in a spoken dialog ' \
        'exchanging the transcripts of a natural real-time conversation.' \
        'Keep your responses short, generally two or three sentences for chatty scenarios.'
    end

    def handle_initialization_error(error)
      @logger.error "Initialization error for #{session_id}: #{error.message}"

      session_data = self.class.active_sessions[session_id]
      session_data[:is_active] = false if session_data

      begin
        dispatch_event('error', {
                         source: 'initialization',
                         error: error.message
                       })
      rescue StandardError => e
        @logger.error "Error dispatching initialization error event: #{e.message}"
      end
    end

    def send_audio_content_start
      session_data = self.class.active_sessions[session_id]
      return unless session_data&.[](:input_stream)

      event = {
        event: {
          contentStart: {
            promptName: session_data[:prompt_name],
            contentName: session_data[:audio_content_id],
            type: 'AUDIO',
            interactive: true,
            audioInputConfiguration: {
              mediaType: 'audio/lpcm',
              sampleRateHertz: 16_000,
              sampleSizeBits: 16,
              channelCount: 1,
              audioType: 'SPEECH',
              encoding: 'base64'
            }
          }
        }
      }.to_json

      begin
        session_data[:input_stream].signal_chunk_event(bytes: event)
      rescue StandardError => e
        @logger.error "Error sending audio content start: #{e.message}"
      end
    end

    def send_content_end
      session_data = self.class.active_sessions[session_id]
      return unless session_data&.[](:input_stream)

      event = {
        event: {
          contentEnd: {
            promptName: session_data[:prompt_name],
            contentName: session_data[:audio_content_id]
          }
        }
      }.to_json

      begin
        session_data[:input_stream].signal_chunk_event(bytes: event)
      rescue StandardError => e
        @logger.error "Error sending content end: #{e.message}"
      end
    end

    def send_prompt_end
      session_data = self.class.active_sessions[session_id]
      return unless session_data&.[](:input_stream)

      event = {
        event: {
          promptEnd: {
            promptName: session_data[:prompt_name]
          }
        }
      }.to_json

      begin
        session_data[:input_stream].signal_chunk_event(bytes: event)
      rescue StandardError => e
        @logger.error "Error sending prompt end: #{e.message}"
      end
    end

    def send_session_end
      session_data = self.class.active_sessions[session_id]
      return unless session_data&.[](:input_stream)

      event = {
        event: {
          sessionEnd: {}
        }
      }.to_json

      begin
        session_data[:input_stream].signal_chunk_event(bytes: event)
        session_data[:input_stream].signal_end_stream
      rescue StandardError => e
        @logger.error "Error sending session end: #{e.message}"
      end
    end
  end
end
