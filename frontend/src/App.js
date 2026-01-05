import './App.css';
import {Route, Routes} from "react-router-dom"; 
import Homepage from "./pages/HomePage.jsx";
import CommunityPage from "./pages/CommunityPage.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import ProfilePage from "./pages/ProfilePage.jsx";
import ReviewPage from "./pages/ReviewPage.jsx";
import ReviewWritePage from "./pages/ReviewWritePage.jsx";
import SignupPage from "./pages/SignupPage.jsx"

function App() {
  return (
    <Routes>
      <Route path="/" element={<Homepage />} />
      <Route path="/community" element={<CommunityPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/profile" element={<ProfilePage />} />
      <Route path="/review" element={<ReviewPage />} />
      <Route path="/review/new" element={<ReviewWritePage />} />
      <Route path="/signup" element={<SignupPage />} />
    </Routes>
  )
};

export default App;
