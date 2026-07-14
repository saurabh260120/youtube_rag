import React, { useState } from 'react';

export default function Quiz() {
    const [videoLink, setVideoLink] = useState('');
    const [quizData, setQuizData] = useState(null);
    const [selectedAnswers, setSelectedAnswers] = useState({});
    const [submitted, setSubmitted] = useState(false);
    const [score, setScore] = useState({ correct: 0, incorrect: 0 });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const questions = quizData?.quiz ?? [];

    const handleFetchQuiz = async () => {
        if (!videoLink.trim()) {
            setError('Please enter a YouTube video link.');
            return;
        }

        setLoading(true);
        setError(null);
        setQuizData(null);
        setSelectedAnswers({});
        setSubmitted(false);
        setScore({ correct: 0, incorrect: 0 });

        try {
            const response = await fetch('http://127.0.0.1:8000/generateQuiz', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ "youtubeUrl": videoLink, "startTime": "0", "endTime": "60" }),
            });

            if (!response.ok) {
                throw new Error(`Quiz API returned ${response.status}`);
            }

            const data = await response.json();
            const fetchedQuestions = data?.quiz?.quiz ?? data?.quiz ?? [];

            if (!Array.isArray(fetchedQuestions) || fetchedQuestions.length === 0) {
                if(data?.message) {
                    throw new Error(data.message);
                }
                throw new Error('No quiz questions were returned.');
            }

            setQuizData({ quiz: fetchedQuestions });
        } catch (fetchError) {
            console.error('Error fetching quiz:', fetchError);
            setError(fetchError.message ?? 'Failed to fetch quiz.');
        } finally {
            setLoading(false);
        }
    };

    const handleOptionChange = (questionIndex, option) => {
        setSelectedAnswers((prev) => ({ ...prev, [questionIndex]: option }));
    };

    const handleSubmit = () => {
        let correct = 0;
        let incorrect = 0;

        questions.forEach((question, index) => {
            const selected = selectedAnswers[index];
            if (selected === question.correct_answer) {
                correct += 1;
            } else {
                incorrect += 1;
            }
        });

        setScore({ correct, incorrect });
        setSubmitted(true);
    };

    const buildYouTubeUrl = (question) => {
        if (!question?.start_time && question?.start_time !== 0) {
            return null;
        }

        const seconds = Math.floor(question.start_time);
        const url=new URL(videoLink);
        const video_id= url.searchParams.get("v");
        return `https://www.youtube.com/watch?v=${video_id}&t=${seconds}`;
    };

    return (
        <div className="max-w-3xl mx-auto p-4">
            <h1 className="text-2xl font-bold mb-4">Interactive Quiz</h1>
            <p className="mb-6 text-gray-700">Paste a YouTube video link, fetch the generated quiz, then submit your answers.</p>

            <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-[1fr_auto]">
                <input
                    type="text"
                    placeholder="Enter YouTube video link"
                    className="border p-2 rounded w-full"
                    value={videoLink}
                    onChange={(e) => setVideoLink(e.target.value)}
                />
                <button
                    type="button"
                    onClick={handleFetchQuiz}
                    disabled={loading}
                    className="bg-blue-600 disabled:bg-blue-300 hover:bg-blue-700 text-white py-2 px-5 rounded-md"
                >
                    {loading ? 'Loading...' : 'Fetch Quiz'}
                </button>
            </div>

            {error && <div className="mb-4 text-red-600">{error}</div>}

            {quizData && (
                <>
                    <div className="space-y-6">
                        {questions.map((question, index) => {
                            const selected = selectedAnswers[index];
                            const optionClassMap = (option) => {
                                const optionIsSelected = selected === option;
                                const optionIsCorrect = submitted && option === question.correct_answer;
                                if (optionIsSelected) {
                                    return optionIsCorrect
                                        ? 'text-green-700 font-semibold'
                                        : 'text-red-700 font-semibold';
                                }
                                return optionIsCorrect ? 'text-green-700' : 'text-gray-800';
                            };

                            return (
                                <div key={index} className="p-4 border rounded-lg bg-white shadow-sm">
                                    <p className="font-semibold mb-3">{index + 1}. {question.question}</p>
                                    <div className="space-y-2">
                                        {question.options.map((option) => (
                                            <label
                                                key={option}
                                                className={`flex items-center space-x-3 rounded-md p-2 hover:bg-gray-50 ${submitted ? 'cursor-default' : 'cursor-pointer'}`}
                                            >
                                                <input
                                                    type="radio"
                                                    name={`question-${index}`}
                                                    value={option}
                                                    checked={selected === option}
                                                    disabled={submitted}
                                                    onChange={() => handleOptionChange(index, option)}
                                                    className="form-radio h-4 w-4 text-blue-600"
                                                />
                                                <span className={optionClassMap(option)}>{option}</span>
                                            </label>
                                        ))}
                                    </div>
                                    {submitted && selected !== question.correct_answer && (
                                        <div className="mt-3 text-sm text-red-600 space-y-2">
                                            <p>Correct answer: {question.correct_answer}</p>
                                            {buildYouTubeUrl(question) && (
                                                <a
                                                    href={buildYouTubeUrl(question)}
                                                    target="_blank"
                                                    rel="noreferrer"
                                                    className="inline-block text-blue-600 underline"
                                                >
                                                    Revisit this part of the video ({Math.floor(question.start_time)}s)
                                                </a>
                                            )}
                                        </div>
                                    )}
                                    {submitted && selected === question.correct_answer && (
                                        <div className="mt-3 text-sm text-green-600 space-y-2">
                                            <p>Great job! {question.explanation}</p>
                                            {buildYouTubeUrl(question) && (
                                                <a
                                                    href={buildYouTubeUrl(question)}
                                                    target="_blank"
                                                    rel="noreferrer"
                                                    className="inline-block text-blue-600 underline"
                                                >
                                                    Revisit this part of the video ({Math.floor(question.start_time)}s)
                                                </a>
                                            )}
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>

                    <div className="mt-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                        <button
                            type="button"
                            onClick={handleSubmit}
                            className="bg-blue-600 hover:bg-blue-700 text-white py-2 px-5 rounded-md"
                        >
                            Submit Answers
                        </button>
                        {submitted && (
                            <div className="text-lg font-semibold">
                                <span className="text-green-700">Correct: {score.correct}</span>
                                <span className="mx-4">|</span>
                                <span className="text-red-700">Incorrect: {score.incorrect}</span>
                            </div>
                        )}
                    </div>
                </>
            )}
        </div>
    );
}
