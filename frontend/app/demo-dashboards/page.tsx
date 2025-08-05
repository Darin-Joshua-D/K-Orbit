import Link from 'next/link';

export default function DemoDashboardsPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background/80 to-primary/10 relative overflow-hidden">
      {/* Background glass elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/5 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-secondary/5 rounded-full blur-3xl animate-pulse" style={{animationDelay: '2s'}}></div>
      </div>

      <div className="relative z-10 p-8">
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="text-center mb-12">
            <h1 className="text-4xl font-bold gradient-text mb-4">
              K-Orbit Dashboard Preview
            </h1>
            <p className="text-muted-foreground text-lg">
              Explore all dashboard types and UI components
            </p>
          </div>

          {/* Navigation Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
            {/* Auth Pages */}
            <div className="glass-card p-6 hover:scale-105 transition-all duration-300">
              <div className="text-center">
                <div className="w-16 h-16 bg-gradient-to-br from-primary/20 to-blue-600/20 rounded-xl mx-auto mb-4 flex items-center justify-center">
                  <span className="text-2xl">🔐</span>
                </div>
                <h3 className="text-xl font-semibold mb-4">Authentication</h3>
                <div className="space-y-2">
                  <Link href="/auth/login" className="btn-primary w-full block">
                    Login Page
                  </Link>
                  <Link href="/auth/register" className="btn-outline w-full block">
                    Register Page
                  </Link>
                </div>
              </div>
            </div>

            {/* Learner Dashboard */}
            <div className="glass-card p-6 hover:scale-105 transition-all duration-300">
              <div className="text-center">
                <div className="w-16 h-16 bg-gradient-to-br from-blue-500/20 to-cyan-600/20 rounded-xl mx-auto mb-4 flex items-center justify-center">
                  <span className="text-2xl">🎓</span>
                </div>
                <h3 className="text-xl font-semibold mb-4">Learner Dashboard</h3>
                <div className="space-y-2">
                  <Link href="/dashboard/learner" className="btn-primary w-full block">
                    View Learner UI
                  </Link>
                  <p className="text-sm text-muted-foreground">Course progress, XP, achievements</p>
                </div>
              </div>
            </div>

            {/* SME Dashboard */}
            <div className="glass-card p-6 hover:scale-105 transition-all duration-300">
              <div className="text-center">
                <div className="w-16 h-16 bg-gradient-to-br from-purple-500/20 to-pink-600/20 rounded-xl mx-auto mb-4 flex items-center justify-center">
                  <span className="text-2xl">👨‍🏫</span>
                </div>
                <h3 className="text-xl font-semibold mb-4">SME Dashboard</h3>
                <div className="space-y-2">
                  <Link href="/dashboard/sme" className="btn-primary w-full block">
                    View SME UI
                  </Link>
                  <p className="text-sm text-muted-foreground">Content creation, analytics</p>
                </div>
              </div>
            </div>

            {/* Glass Showcase */}
            <div className="glass-card p-6 hover:scale-105 transition-all duration-300">
              <div className="text-center">
                <div className="w-16 h-16 bg-gradient-to-br from-green-500/20 to-teal-600/20 rounded-xl mx-auto mb-4 flex items-center justify-center">
                  <span className="text-2xl">✨</span>
                </div>
                <h3 className="text-xl font-semibold mb-4">Glass UI Showcase</h3>
                <div className="space-y-2">
                  <Link href="/glass-showcase" className="btn-primary w-full block">
                    View All Effects
                  </Link>
                  <p className="text-sm text-muted-foreground">Complete design system demo</p>
                </div>
              </div>
            </div>

            {/* Test Styling */}
            <div className="glass-card p-6 hover:scale-105 transition-all duration-300">
              <div className="text-center">
                <div className="w-16 h-16 bg-gradient-to-br from-orange-500/20 to-red-600/20 rounded-xl mx-auto mb-4 flex items-center justify-center">
                  <span className="text-2xl">🎨</span>
                </div>
                <h3 className="text-xl font-semibold mb-4">Styling Test</h3>
                <div className="space-y-2">
                  <Link href="/test-styling" className="btn-primary w-full block">
                    Test Components
                  </Link>
                  <p className="text-sm text-muted-foreground">Button and component tests</p>
                </div>
              </div>
            </div>

            {/* AI Chat Info */}
            <div className="glass-card p-6 hover:scale-105 transition-all duration-300">
              <div className="text-center">
                <div className="w-16 h-16 bg-gradient-to-br from-violet-500/20 to-purple-600/20 rounded-xl mx-auto mb-4 flex items-center justify-center">
                  <span className="text-2xl">🤖</span>
                </div>
                <h3 className="text-xl font-semibold mb-4">AI Coach Chat</h3>
                <div className="space-y-2">
                  <p className="text-sm text-muted-foreground mb-2">Available on authenticated pages</p>
                  <p className="text-xs text-muted-foreground">Look for floating chat button (bottom right)</p>
                </div>
              </div>
            </div>
          </div>

          {/* Instructions */}
          <div className="glass-card p-8 text-center">
            <h2 className="text-2xl font-bold mb-4">How to Explore</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-left">
              <div>
                <h4 className="font-semibold mb-2">🔐 Authentication Flow:</h4>
                <ol className="text-sm text-muted-foreground space-y-1">
                  <li>1. Visit Login/Register pages</li>
                  <li>2. Create account or sign in</li>
                  <li>3. Get redirected to dashboard</li>
                  <li>4. See role-specific interface</li>
                </ol>
              </div>
              <div>
                <h4 className="font-semibold mb-2">🎨 UI Components:</h4>
                <ol className="text-sm text-muted-foreground space-y-1">
                  <li>1. Glass morphism cards</li>
                  <li>2. Gradient buttons & animations</li>
                  <li>3. Modern form designs</li>
                  <li>4. Responsive layouts</li>
                </ol>
              </div>
            </div>
          </div>

          {/* Back to Home */}
          <div className="text-center mt-8">
            <Link href="/" className="btn-outline">
              ← Back to Homepage
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
} 