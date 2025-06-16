#!/usr/bin/env ruby
require_relative 'audio_service'
require_relative 'portaudio'
require 'base64'
require 'securerandom'
require 'logger'

module NovaSonic
  class SimpleExample
    def initialize
      @session_id = SecureRandom.uuid
      @logger = Logger.new($stdout)
      @logger.level = Logger::INFO
      @audio_service = AudioService.new(@session_id, @logger)
      @audio_handler = PortAudioHandler.new(@logger)
      @running = false
      @current_stage = nil
    end

    def start
      setup_event_handlers
      setup_audio_handlers
      setup_session
      start_audio_streams
    end

    def stop
      @running = false
      @audio_handler.stop
      @audio_service.close_session
    end

    private

    def setup_event_handlers
      @audio_service.on_event('contentStart') do |data|
        additionalModelFields = data['additionalModelFields']
        additionalModelFields = JSON.parse(additionalModelFields) if additionalModelFields.is_a?(String)

        if additionalModelFields != nil
          stage = additionalModelFields['generationStage']
          @current_stage = stage if stage
        end
      end

      @audio_service.on_event('textOutput') do |data|
        if @current_stage == 'SPECULATIVE' && data['role'] == 'ASSISTANT'
          @logger.info "🎤 #{data['role']}: #{data['content']}"
        elsif data['role'] == 'USER'
          @logger.info "👤 #{data['role']}: #{data['content']}"
        end
      end

      @audio_service.on_event('audioOutput') do |data|
        audio_data = Base64.decode64(data['content'])
        @audio_handler.queue_audio_output(audio_data)
      end

      @audio_service.on_event('error') do |data|
        @logger.error "❌ Error: #{data['error']}"
      end
    end

    def setup_audio_handlers
      @audio_handler.on_audio_input do |raw_pcm|
        unless @audio_handler.echo_cancellation_active?
          @audio_service.stream_audio(Base64.strict_encode64(raw_pcm))
        end
      end
    end

    def setup_session
      @audio_service.setup_session
    end

    def start_audio_streams
      @running = true
      @audio_handler.start
      
      @logger.info "🎤 Audio streaming started"
      @logger.info "🔊 Simple time-based echo cancellation"
    end
  end
end

# Example usage:
if __FILE__ == $PROGRAM_NAME
  example = NovaSonic::SimpleExample.new
  shutdown_requested = false
  
  Signal.trap("INT") do
    puts "\n🛑 IMMEDIATE SHUTDOWN REQUESTED"
    shutdown_requested = true
    # Give it 1 second to cleanup, then force exit
    Thread.new do
      sleep 1
      puts "🚨 FORCING EXIT NOW!"
      exit!(0)
    end
  end
  
  Signal.trap("TERM") do
    puts "\n🛑 TERMINATE SIGNAL - IMMEDIATE EXIT"
    exit!(0)
  end
  
  begin
    puts "🚀 Starting Nova Sonic (Simple Echo Cancellation)..."
    puts "🎤 Should work for multiple conversations!"
    puts "🔊 1-second echo cancellation after AI speech"
    puts "Press Ctrl+C to stop"
    
    example.start
    
    until shutdown_requested
      sleep 0.05  # Faster response
    end
    
  rescue StandardError => e
    puts "❌ Error: #{e.message}"
  ensure
    puts "🛑 Attempting quick cleanup..."
    begin
      # Try cleanup but don't wait long
      example.stop
      sleep 0.2  # Give it 200ms max
    rescue
      # Ignore cleanup errors
    end
    puts "👋 Goodbye!"
  end
end 