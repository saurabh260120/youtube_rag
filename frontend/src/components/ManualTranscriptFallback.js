import React, { useState } from 'react';

export default function ManualTranscriptFallback({ videoLink, onTranscriptSubmitted }) {
    const [manualTranscript, setManualTranscript] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const [submitError, setSubmitError] = useState(null);
    const [submitSuccess, setSubmitSuccess] = useState(null);

    const handleSubmitManualTranscript = async () => {
        if (!manualTranscript.trim()) {
            setSubmitError('Please paste the transcript text first.');
            return;
        }

        setSubmitting(true);
        setSubmitError(null);
        setSubmitSuccess(null);

        try {
            const response = await fetch('/api/submitManualTranscript', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    youtubeUrl: videoLink,
                    transcript: manualTranscript,
                }),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data?.detail || data?.message || 'Failed to submit manual transcript.');
            }

            setSubmitSuccess(data.message || 'Transcript submitted successfully!');
            
            if (onTranscriptSubmitted) {
                onTranscriptSubmitted(data);
            }
        } catch (err) {
            console.error('Error submitting manual transcript:', err);
            setSubmitError(err.message || 'Something went wrong while submitting the transcript.');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="mt-6 rounded-lg border-2 border-dashed border-amber-300 bg-amber-50 p-5">
            <div className="mb-4">
                <h3 className="text-lg font-semibold text-amber-900">
                    ⚠️ Automatic transcript fetch failed
                </h3>
                <p className="mt-1 text-sm text-amber-800">
                    We couldn't fetch the transcript automatically. You can manually copy it from{' '}
                    <a
                        href="https://youtubetotranscript.com/"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-medium text-blue-600 underline hover:text-blue-800"
                    >
                        https://youtubetotranscript.com/
                    </a>{' '}
                    and paste it below.
                </p>
            </div>

            {/* Instructions */}
            <div className="mb-4 rounded-md bg-white p-3 text-sm text-gray-700 shadow-sm">
                <p className="font-medium text-gray-900">Steps:</p>
                <ol className="ml-5 mt-1 list-decimal space-y-1">
                    <li>Open <a href="https://youtubetotranscript.com/" target="_blank" rel="noopener noreferrer" className="text-blue-600 underline">youtubetotranscript.com</a></li>
                    <li>Paste your YouTube video URL and click "Get Transcript"</li>
                    <li>Copy the entire transcript text (with or without timestamps)</li>
                    <li>Paste it in the box below and click "Submit"</li>
                </ol>
                <p className="mt-2 text-xs text-gray-500">
                    The transcript can be in timestamped format (e.g., "00:00:00 text...") or plain text.
                </p>
            </div>

            {/* Textarea */}
            <textarea
                value={manualTranscript}
                onChange={(e) => setManualTranscript(e.target.value)}
                placeholder="Paste the transcript here..."
                rows={8}
                className="w-full rounded-md border border-gray-300 p-3 text-sm shadow-sm focus:border-amber-400 focus:outline-none focus:ring-1 focus:ring-amber-400"
            />

            {/* Submit button */}
            <button
                type="button"
                onClick={handleSubmitManualTranscript}
                disabled={submitting || !manualTranscript.trim()}
                className="mt-3 rounded-md bg-amber-600 px-5 py-2 text-sm font-medium text-white hover:bg-amber-700 disabled:bg-amber-300"
            >
                {submitting ? 'Submitting...' : 'Submit Manual Transcript'}
            </button>

            {/* Error message */}
            {submitError && (
                <div className="mt-3 text-sm text-red-600">{submitError}</div>
            )}

            {/* Success message */}
            {submitSuccess && (
                <div className="mt-3 rounded-md bg-green-50 p-3 text-sm text-green-700">
                    ✅ {submitSuccess}
                    <p className="mt-1 text-green-600">
                        Your transcript has been queued for processing. Please check back after some time.
                    </p>
                </div>
            )}
        </div>
    );
}