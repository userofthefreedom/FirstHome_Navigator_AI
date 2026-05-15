import { createBrowserRouter } from "react-router";
import { RootLayout } from "./components/RootLayout";
import { HomePage } from "./components/HomePage";
import { ConditionPage } from "./components/ConditionPage";
import { RecommendationPage } from "./components/RecommendationPage";
import { FinancePage } from "./components/FinancePage";
import { CommunityPage } from "./components/CommunityPage";
import { MapPage } from "./components/MapPage";
import { ConfirmationPage } from "./components/ConfirmationPage";

export const router = createBrowserRouter([
  {
    path: "/",
    Component: RootLayout,
    children: [
      { index: true, Component: HomePage },
      { path: "condition", Component: ConditionPage },
      { path: "recommendation", Component: RecommendationPage },
      { path: "finance", Component: FinancePage },
      { path: "community", Component: CommunityPage },
      { path: "map", Component: MapPage },
      { path: "confirmation", Component: ConfirmationPage },
    ],
  },
]);
