import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import HomePage from "./features/main/pages/HomePage";
import CameraPage from "./features/main/pages/CameraPage";
import PreviewPage from "./features/main/pages/PreviewPage";
import ResultPage from "./features/main/pages/ResultPage";
import UploadPage from "./features/main/pages/UploadPage";
import LoginPage from "./features/auth/LoginPage";
import SignupPage from "./features/auth/SignupPage";
import ProfilePage from "./features/profile/ProfilePage";
import CommunityPage from "./features/community/CommunityPage";
import ReviewPage from "./features/review/ReviewPage";
import ReviewWritePage from "./features/review/ReviewWritePage";

export default function AppRouter() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/camera" element={<CameraPage />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/preview" element={<PreviewPage />} />
        <Route path="/result" element={<ResultPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/community" element={<CommunityPage />} />
        <Route path="/review" element={<ReviewPage />} />
        <Route path="/review/new" element={<ReviewWritePage />} />
      </Routes>
    </Router>
  );
}
