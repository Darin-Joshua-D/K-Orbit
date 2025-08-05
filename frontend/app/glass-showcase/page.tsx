export default function GlassShowcasePage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background/80 to-primary/10 relative overflow-hidden">
      {/* Animated background elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/5 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-secondary/5 rounded-full blur-3xl animate-pulse" style={{animationDelay: '2s'}}></div>
        <div className="absolute top-3/4 left-1/2 w-64 h-64 bg-accent/5 rounded-full blur-2xl animate-pulse" style={{animationDelay: '4s'}}></div>
      </div>

      <div className="relative z-10 p-8">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold gradient-text mb-4">
            K-Orbit Glass UI Showcase
          </h1>
          <p className="text-muted-foreground text-lg">
            Modern glass morphism design system in action
          </p>
        </div>

        {/* Navigation Glass Bar */}
        <nav className="glass backdrop-blur-lg rounded-2xl p-4 mb-8 max-w-4xl mx-auto">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-gradient-to-br from-primary to-secondary rounded-lg"></div>
              <span className="font-bold gradient-text">K-Orbit</span>
            </div>
            <div className="flex space-x-4">
              <button className="btn-glass">Features</button>
              <button className="btn-glass">About</button>
              <button className="btn-primary">Get Started</button>
            </div>
          </div>
        </nav>

        {/* Glass Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12 max-w-7xl mx-auto">
          {/* Standard Glass Card */}
          <div className="glass-card p-6 hover:scale-105 transition-all duration-300 group">
            <div className="text-center">
              <div className="w-16 h-16 bg-gradient-to-br from-primary/20 to-blue-600/20 rounded-xl mx-auto mb-4 flex items-center justify-center group-hover:shadow-lg transition-shadow">
                <span className="text-2xl">🚀</span>
              </div>
              <h3 className="text-xl font-semibold mb-2">Fast Performance</h3>
              <p className="text-muted-foreground">Optimized for speed and efficiency</p>
            </div>
          </div>

          {/* Frosted Glass Card */}
          <div className="frosted-glass p-6 hover:scale-105 transition-all duration-300 group">
            <div className="text-center">
              <div className="w-16 h-16 bg-gradient-to-br from-secondary/20 to-purple-600/20 rounded-xl mx-auto mb-4 flex items-center justify-center group-hover:shadow-lg transition-shadow">
                <span className="text-2xl">🎨</span>
              </div>
              <h3 className="text-xl font-semibold mb-2">Beautiful Design</h3>
              <p className="text-muted-foreground">Modern glass morphism effects</p>
            </div>
          </div>

          {/* Dark Glass Card */}
          <div className="glass-card-dark p-6 hover:scale-105 transition-all duration-300 group">
            <div className="text-center">
              <div className="w-16 h-16 bg-gradient-to-br from-accent/20 to-green-600/20 rounded-xl mx-auto mb-4 flex items-center justify-center group-hover:shadow-lg transition-shadow">
                <span className="text-2xl">🛡️</span>
              </div>
              <h3 className="text-xl font-semibold mb-2 text-white">Secure</h3>
              <p className="text-gray-300">Enterprise-grade security</p>
            </div>
          </div>
        </div>

        {/* Button Showcase */}
        <div className="glass-card p-8 mb-12 max-w-4xl mx-auto">
          <h2 className="text-2xl font-bold mb-6 text-center">Button Styles</h2>
          <div className="flex flex-wrap gap-4 justify-center">
            <button className="btn-primary">Primary Button</button>
            <button className="btn-secondary">Secondary Button</button>
            <button className="btn-outline">Outline Button</button>
            <button className="btn-ghost">Ghost Button</button>
            <button className="btn-glass">Glass Button</button>
          </div>
        </div>

        {/* Interactive Elements */}
        <div className="glass-card p-8 mb-12 max-w-4xl mx-auto">
          <h2 className="text-2xl font-bold mb-6 text-center">Interactive Elements</h2>
          <div className="space-y-6">
            {/* Progress bars */}
            <div>
              <label className="block text-sm font-medium mb-2">Progress Example</label>
              <div className="progress">
                <div className="progress-indicator" style={{width: '70%'}}></div>
              </div>
            </div>

            {/* Badges */}
            <div>
              <label className="block text-sm font-medium mb-2">Badges</label>
              <div className="flex gap-2">
                <span className="badge-default">Default</span>
                <span className="badge-secondary">Secondary</span>
                <span className="badge-outline">Outline</span>
              </div>
            </div>

            {/* Form Elements */}
            <div>
              <label className="block text-sm font-medium mb-2">Glass Input</label>
              <input 
                type="text" 
                className="input glass" 
                placeholder="Type something..."
              />
            </div>
          </div>
        </div>

        {/* Feature Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-6xl mx-auto mb-12">
          <div className="glass-card p-8">
            <h3 className="text-xl font-bold mb-4">🎯 AI-Powered Learning</h3>
            <p className="text-muted-foreground mb-4">
              Personalized learning paths powered by advanced AI algorithms that adapt to your pace and style.
            </p>
            <button className="btn-primary w-full">Learn More</button>
          </div>

          <div className="glass-card p-8">
            <h3 className="text-xl font-bold mb-4">🏆 Gamification</h3>
            <p className="text-muted-foreground mb-4">
              Earn points, unlock achievements, and compete with colleagues in a fun learning environment.
            </p>
            <button className="btn-outline w-full">Explore</button>
          </div>
        </div>

        {/* Stats Section */}
        <div className="glass-card p-8 max-w-4xl mx-auto text-center">
          <h2 className="text-2xl font-bold mb-8">Platform Statistics</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div>
              <div className="text-4xl font-bold text-primary mb-2">98%</div>
              <div className="text-sm text-muted-foreground">User Satisfaction</div>
            </div>
            <div>
              <div className="text-4xl font-bold text-secondary mb-2">50K+</div>
              <div className="text-sm text-muted-foreground">Active Learners</div>
            </div>
            <div>
              <div className="text-4xl font-bold text-accent mb-2">1M+</div>
              <div className="text-sm text-muted-foreground">Lessons Completed</div>
            </div>
          </div>
        </div>

        {/* Call to Action */}
        <div className="text-center mt-12">
          <div className="glass-card p-8 max-w-2xl mx-auto">
            <h2 className="text-3xl font-bold mb-4 gradient-text">
              Ready to Experience Modern Learning?
            </h2>
            <p className="text-muted-foreground mb-6">
              Join thousands of learners who have transformed their skills with K-Orbit
            </p>
            <div className="flex gap-4 justify-center">
              <button className="btn-primary">Start Free Trial</button>
              <button className="btn-outline">Watch Demo</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
} 