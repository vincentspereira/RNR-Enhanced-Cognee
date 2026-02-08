import Link from "next/link";
import { Home, Search, FileQuestion } from "lucide-react";
import { Button } from "@/components/atoms/Button";

export default function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 p-6">
      <div className="max-w-lg w-full">
        <div className="bg-white rounded-lg shadow-xl border border-gray-200 p-8">
          {/* 404 Icon */}
          <div className="flex justify-center mb-6">
            <div className="bg-blue-100 rounded-full p-4">
              <FileQuestion className="w-12 h-12 text-blue-500" />
            </div>
          </div>

          {/* Error message */}
          <div className="text-center mb-6">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">404</h1>
            <h2 className="text-xl font-semibold text-gray-800 mb-2">
              Page Not Found
            </h2>
            <p className="text-gray-600">
              The page you are looking for does not exist or has been moved.
            </p>
          </div>

          {/* Suggestions */}
          <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-md">
            <p className="text-sm text-blue-900 font-medium mb-2">
              Here are some helpful links:
            </p>
            <ul className="text-sm text-blue-800 space-y-1">
              <li>
                <Link
                  href="/dashboard"
                  className="hover:underline hover:text-blue-600"
                >
                  Dashboard
                </Link>
              </li>
              <li>
                <Link
                  href="/memories"
                  className="hover:underline hover:text-blue-600"
                >
                  Memories
                </Link>
              </li>
              <li>
                <Link
                  href="/analytics"
                  className="hover:underline hover:text-blue-600"
                >
                  Analytics
                </Link>
              </li>
              <li>
                <Link
                  href="/search"
                  className="hover:underline hover:text-blue-600"
                >
                  Search
                </Link>
              </li>
            </ul>
          </div>

          {/* Actions */}
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Button asChild>
              <Link href="/dashboard">
                <Home className="w-4 h-4 mr-2" />
                Go to Dashboard
              </Link>
            </Button>
            <Button variant="outline" asChild>
              <Link href="/search">
                <Search className="w-4 h-4 mr-2" />
                Search Memories
              </Link>
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
