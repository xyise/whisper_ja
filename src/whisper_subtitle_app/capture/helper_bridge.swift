import AVFoundation
import CoreMedia
import Dispatch
import Foundation
import ScreenCaptureKit

struct AppDescriptor: Codable {
    let name: String
    let bundleIdentifier: String
    let processId: Int32
}

enum BridgeError: LocalizedError {
    case missingCommand
    case missingBundleIdentifier
    case missingApplication(String)
    case noDisplay
    case streamNotStarted

    var errorDescription: String? {
        switch self {
        case .missingCommand:
            return "Expected a command: list-apps or capture."
        case .missingBundleIdentifier:
            return "The capture command requires --bundle-id."
        case .missingApplication(let bundleIdentifier):
            return "Could not find a captureable application for bundle id: \(bundleIdentifier)."
        case .noDisplay:
            return "Could not find a display to capture."
        case .streamNotStarted:
            return "Failed to start the ScreenCaptureKit stream."
        }
    }
}

final class AudioStreamOutput: NSObject, SCStreamOutput, SCStreamDelegate {
    private let targetFormat: AVAudioFormat
    private let outputHandle = FileHandle.standardOutput
    private let errorHandle = FileHandle.standardError

    init(sampleRate: Double) {
        self.targetFormat = AVAudioFormat(commonFormat: .pcmFormatFloat32, sampleRate: sampleRate, channels: 1, interleaved: true)!
        super.init()
    }

    func stream(_ stream: SCStream, didStopWithError error: any Error) {
        let data = Data(("screen capture stopped: \(error.localizedDescription)\n").utf8)
        try? errorHandle.write(contentsOf: data)
        exit(1)
    }

    func stream(_ stream: SCStream, didOutputSampleBuffer sampleBuffer: CMSampleBuffer, of outputType: SCStreamOutputType) {
        guard outputType == .audio, sampleBuffer.isValid else {
            return
        }

        do {
            guard let pcmBuffer = try makePCMBuffer(from: sampleBuffer) else {
                return
            }
            guard let converted = convertBuffer(pcmBuffer) else {
                return
            }
            let audioBuffer = converted.audioBufferList.pointee.mBuffers
            guard let data = audioBuffer.mData, audioBuffer.mDataByteSize > 0 else {
                return
            }
            let payload = Data(bytes: data, count: Int(audioBuffer.mDataByteSize))
            try outputHandle.write(contentsOf: payload)
        } catch {
            let data = Data(("audio conversion error: \(error.localizedDescription)\n").utf8)
            try? errorHandle.write(contentsOf: data)
        }
    }

    private func makePCMBuffer(from sampleBuffer: CMSampleBuffer) throws -> AVAudioPCMBuffer? {
        guard let formatDescription = CMSampleBufferGetFormatDescription(sampleBuffer),
              let streamDescriptionPtr = CMAudioFormatDescriptionGetStreamBasicDescription(formatDescription) else {
            return nil
        }

        var streamDescription = streamDescriptionPtr.pointee
        guard let inputFormat = AVAudioFormat(streamDescription: &streamDescription) else {
            return nil
        }

        let frameCount = AVAudioFrameCount(CMSampleBufferGetNumSamples(sampleBuffer))
        guard let pcmBuffer = AVAudioPCMBuffer(pcmFormat: inputFormat, frameCapacity: frameCount) else {
            return nil
        }
        pcmBuffer.frameLength = frameCount

        let status = CMSampleBufferCopyPCMDataIntoAudioBufferList(
            sampleBuffer,
            at: 0,
            frameCount: Int32(frameCount),
            into: pcmBuffer.mutableAudioBufferList
        )
        guard status == noErr else {
            throw NSError(domain: NSOSStatusErrorDomain, code: Int(status))
        }

        return pcmBuffer
    }

    private func convertBuffer(_ buffer: AVAudioPCMBuffer) -> AVAudioPCMBuffer? {
        guard let converter = AVAudioConverter(from: buffer.format, to: targetFormat) else {
            return nil
        }

        let capacity = AVAudioFrameCount(Double(buffer.frameLength) * targetFormat.sampleRate / buffer.format.sampleRate) + 1024
        guard let converted = AVAudioPCMBuffer(pcmFormat: targetFormat, frameCapacity: capacity) else {
            return nil
        }

        var consumed = false
        var error: NSError?
        let status = converter.convert(to: converted, error: &error) { _, outStatus in
            if consumed {
                outStatus.pointee = .noDataNow
                return nil
            }
            consumed = true
            outStatus.pointee = .haveData
            return buffer
        }

        if let error {
            let data = Data(("audio converter failure: \(error.localizedDescription)\n").utf8)
            try? errorHandle.write(contentsOf: data)
            return nil
        }

        guard status == .haveData || converted.frameLength > 0 else {
            return nil
        }
        return converted
    }
}

@main
struct WhisperSubtitleBridge {
    private static var activeStream: SCStream?
    private static var activeOutput: AudioStreamOutput?

    static func main() {
        Task {
            do {
                let arguments = Array(CommandLine.arguments.dropFirst())
                guard let command = arguments.first else {
                    throw BridgeError.missingCommand
                }

                switch command {
                case "list-apps":
                    try await listApps()
                    exit(0)
                case "capture":
                    try await capture(arguments: Array(arguments.dropFirst()))
                default:
                    throw BridgeError.missingCommand
                }
            } catch {
                let data = Data(("\(error.localizedDescription)\n").utf8)
                try? FileHandle.standardError.write(contentsOf: data)
                exit(1)
            }
        }
        dispatchMain()
    }

    private static func listApps() async throws {
        let content = try await SCShareableContent.excludingDesktopWindows(false, onScreenWindowsOnly: true)
        let descriptors = content.applications
            .filter { !$0.bundleIdentifier.isEmpty }
            .map {
                AppDescriptor(
                    name: $0.applicationName,
                    bundleIdentifier: $0.bundleIdentifier,
                    processId: $0.processID
                )
            }
            .sorted { lhs, rhs in
                lhs.name.localizedCaseInsensitiveCompare(rhs.name) == .orderedAscending
            }

        let payload = try JSONEncoder().encode(descriptors)
        try FileHandle.standardOutput.write(contentsOf: payload)
    }

    private static func capture(arguments: [String]) async throws {
        let bundleIdentifier = try parseBundleIdentifier(arguments: arguments)
        let requestedSampleRate = parseSampleRate(arguments: arguments)
        let content = try await SCShareableContent.excludingDesktopWindows(false, onScreenWindowsOnly: true)

        guard let application = content.applications.first(where: { $0.bundleIdentifier == bundleIdentifier }) else {
            throw BridgeError.missingApplication(bundleIdentifier)
        }
        guard let display = content.displays.first else {
            throw BridgeError.noDisplay
        }

        let filter = SCContentFilter(display: display, including: [application], exceptingWindows: [])
        let configuration = SCStreamConfiguration()
        configuration.capturesAudio = true
        configuration.excludesCurrentProcessAudio = true
        configuration.sampleRate = Int(requestedSampleRate)
        configuration.channelCount = 1
        configuration.minimumFrameInterval = CMTime(value: 1, timescale: 30)
        configuration.queueDepth = 3

        let output = AudioStreamOutput(sampleRate: requestedSampleRate)
        let stream = SCStream(filter: filter, configuration: configuration, delegate: output)
        try stream.addStreamOutput(output, type: .audio, sampleHandlerQueue: DispatchQueue(label: "bridge.audio.output"))
        try await stream.startCapture()
        activeOutput = output
        activeStream = stream
    }

    private static func parseBundleIdentifier(arguments: [String]) throws -> String {
        guard let index = arguments.firstIndex(of: "--bundle-id"), arguments.indices.contains(index + 1) else {
            throw BridgeError.missingBundleIdentifier
        }
        return arguments[index + 1]
    }

    private static func parseSampleRate(arguments: [String]) -> Double {
        guard let index = arguments.firstIndex(of: "--sample-rate"), arguments.indices.contains(index + 1), let sampleRate = Double(arguments[index + 1]) else {
            return 16_000
        }
        return sampleRate
    }
}
