// Root application component: sets up routing, global data-fetching context,
// and UI providers (tooltip, toast) that wrap the entire component tree.

import { Switch, Route, Router as WouterRouter } from "wouter";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import NotFound from "@/pages/not-found";
import Home from "@/pages/home";

// Single shared QueryClient instance for all TanStack Query hooks in the app
const queryClient = new QueryClient();

function Router() {
  return (
    // Switch renders only the first matching route
    <Switch>
      <Route path="/" component={Home} />
      <Route component={NotFound} />  {/* fallback route for any unmatched path */}
    </Switch>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        {/* Strip trailing slash from BASE_URL so wouter routes match correctly */}
        <WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, "")}>
          <Router />
        </WouterRouter>
        <Toaster />  {/* global toast notification container */}
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;
