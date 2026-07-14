import "./index.css";
import Navigation from "./components/navbar";
import { BrowserRouter, Routes, Route } from "react-router-dom";

import Summary from './components/summary.js'
import Quiz from './components/quiz.js'
import AskQuestion from './components/askQuestion.js'

export function App() {
  return (
    <BrowserRouter>
      <div>
        <Navigation />
        <Routes>
          <Route path="/summary" element={<Summary />} />
          <Route path="/ask" element={<AskQuestion />} />
          <Route path="/" element={<Quiz />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;
