#!/usr/bin/env ruby
require 'ffi-portaudio'
require 'base64'

class PortAudioHandler
  include FFI::PortAudio
  
  INPUT_SAMPLE_RATE = 16000
  OUTPUT_SAMPLE_RATE = 16000
  CHANNELS = 1
  FRAMES_PER_BUFFER = 2048
  
  def initialize(logger)
    @logger = logger
    @running = false
    @input_stream = nil
    @output_stream = nil
    @input_callback = nil
    
    # Much simpler buffering
    @sample_buffer = []
    @buffer_mutex = Mutex.new
    @playing_audio = false
    @last_output_time = Time.now
    
    initialize_portaudio
  end

  def on_audio_input(&block)
    @input_callback = block
  end

  def queue_audio_output(audio_data)
    @buffer_mutex.synchronize do
      # Convert raw PCM to samples and add to buffer
      new_samples = audio_data.unpack('s*')
      @sample_buffer.concat(new_samples)
      @playing_audio = true
      @last_output_time = Time.now
      
      @logger.debug "Queued #{new_samples.length} samples, buffer now #{@sample_buffer.length} samples"
    end
  end

  def start
    return if @running
    
    @running = true
    start_input_stream
    start_output_stream
    @logger.info "🎵 Fixed PortAudio streams started"
  end

  def stop
    return unless @running
    
    @running = false
    
    # Force exit in background if this takes too long
    timeout_thread = Thread.new do
      sleep 0.5
      puts "🚨 AUDIO SHUTDOWN TIMEOUT - FORCING EXIT!"
      exit!(0)
    end
    
    begin
      stop_streams
      cleanup_portaudio
      @logger.info "🔇 PortAudio streams stopped"
      
      # Cancel timeout
      timeout_thread.kill
    rescue
      # If cleanup fails, just exit
      puts "⚠️ Audio cleanup failed, forcing exit"
      exit!(0)
    end
  end

  def echo_cancellation_active?
    # Simple time-based approach: block input for 1 second after last audio output
    @playing_audio && (Time.now - @last_output_time) < 1.0
  end

  private

  def initialize_portaudio
    result = API.Pa_Initialize
    if result == :paNoError
      @logger.info "🎤 PortAudio initialized"
    else
      @logger.error "❌ Failed to initialize PortAudio: #{result}"
    end
  end

  def start_input_stream
    @input_stream = InputStreamHandler.new(@logger, @input_callback, self)
    
    input_device = API.Pa_GetDefaultInputDevice
    if input_device < 0
      @logger.error "❌ No default input device found"
      return
    end

    input_params = API::PaStreamParameters.new
    input_params[:device] = input_device
    input_params[:channelCount] = CHANNELS
    input_params[:sampleFormat] = API::Int16
    input_params[:suggestedLatency] = 0.05
    input_params[:hostApiSpecificStreamInfo] = nil

    @input_stream.open(input_params, nil, INPUT_SAMPLE_RATE, FRAMES_PER_BUFFER)
    @input_stream.start
    @logger.info "🎤 Input stream started"
  end

  def start_output_stream
    @output_stream = OutputStreamHandler.new(@logger, @sample_buffer, @buffer_mutex, self)
    
    output_device = API.Pa_GetDefaultOutputDevice
    if output_device < 0
      @logger.error "❌ No default output device found"
      return
    end

    output_params = API::PaStreamParameters.new
    output_params[:device] = output_device
    output_params[:channelCount] = CHANNELS
    output_params[:sampleFormat] = API::Int16
    output_params[:suggestedLatency] = 0.1
    output_params[:hostApiSpecificStreamInfo] = nil

    @output_stream.open(nil, output_params, OUTPUT_SAMPLE_RATE, FRAMES_PER_BUFFER)
    @output_stream.start
    @logger.info "🔊 Output stream started"
  end

  def stop_streams
    @running = false
    
    begin
      if @input_stream
        @input_stream.stop rescue nil
        @input_stream.close rescue nil
        @input_stream = nil
      end
    rescue => e
      @logger.error "Error stopping input stream: #{e.message}"
    end

    begin
      if @output_stream
        @output_stream.stop rescue nil
        @output_stream.close rescue nil
        @output_stream = nil
      end
    rescue => e
      @logger.error "Error stopping output stream: #{e.message}"
    end
  end

  def cleanup_portaudio
    API.Pa_Terminate
  end

  def mark_output_finished
    @buffer_mutex.synchronize do
      if @sample_buffer.empty?
        @playing_audio = false
        @logger.debug "Output finished - microphone re-enabled"
      end
    end
  end

  # Input stream handler class
  class InputStreamHandler < FFI::PortAudio::Stream
    def initialize(logger, callback, parent_handler)
      @logger = logger
      @callback = callback
      @parent_handler = parent_handler
      @input_count = 0
    end

    def process(input, output, frameCount, timeInfo, statusFlags, userData)
      @input_count += 1
      
      # Log periodically
      if @input_count % 1000 == 0
        echo_active = @parent_handler.echo_cancellation_active?
        @logger.debug "Input callback ##{@input_count}, echo_cancellation=#{echo_active}"
      end
      
      unless @parent_handler.echo_cancellation_active?
        if input && frameCount > 0
          audio_data = input.read_array_of_int16(frameCount * CHANNELS)
          raw_pcm = audio_data.pack('s*')
          @callback.call(raw_pcm) if @callback
        end
      end
      
      :paContinue
    end
  end

  # Fixed output stream handler class
  class OutputStreamHandler < FFI::PortAudio::Stream
    def initialize(logger, sample_buffer, mutex, parent_handler)
      @logger = logger
      @sample_buffer = sample_buffer
      @mutex = mutex
      @parent_handler = parent_handler
      @output_count = 0
    end

    def process(input, output, frameCount, timeInfo, statusFlags, userData)
      @output_count += 1
      required_samples = frameCount * CHANNELS
      
      @mutex.synchronize do
        if @sample_buffer.length >= required_samples
          # We have enough samples
          samples = @sample_buffer.shift(required_samples)
          output.write_array_of_int16(samples)
          
          if @output_count % 100 == 0
            @logger.debug "Output ##{@output_count}: played #{required_samples} samples, #{@sample_buffer.length} remaining"
          end
          
        elsif @sample_buffer.length > 0
          # Use what we have and pad with silence
          available_samples = @sample_buffer.shift(@sample_buffer.length)
          padding_needed = required_samples - available_samples.length
          complete_samples = available_samples + [0] * padding_needed
          output.write_array_of_int16(complete_samples)
          
          @logger.debug "Output ##{@output_count}: used #{available_samples.length} samples, padded #{padding_needed}"
          
        else
          # Output silence
          silence = [0] * required_samples
          output.write_array_of_int16(silence)
          
          # Mark output as finished when buffer is empty
          @parent_handler.mark_output_finished
        end
      end
      
      :paContinue
    end
  end
end 