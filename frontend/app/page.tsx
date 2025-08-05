import React, { ReactNode } from 'react';
import Link from 'next/link';
import { ArrowRight, Brain, Users, Trophy, BookOpen, MessageSquare, BarChart3 } from 'lucide-react';

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background/80 to-primary/10 relative overflow-hidden">
      {/* Background glass elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/5 rounded-full blur-3xl"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-secondary/5 rounded-full blur-3xl"></div>
      </div>
      <div className="relative z-10">
              {/* Navigation */}
        <nav className="container mx-auto px-4 py-6 glass backdrop-blur-lg rounded-lg mt-4 mx-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-gradient-to-br from-primary to-secondary rounded-lg flex items-center justify-center">
              <Brain className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-bold gradient-text">K-Orbit</span>
          </div>
          <div className="hidden md:flex items-center space-x-8">
            <a href="#features" className="text-muted-foreground hover:text-foreground transition-colors">
              Features
            </a>
            <a href="#how-it-works" className="text-muted-foreground hover:text-foreground transition-colors">
              How It Works
            </a>
            <a href="#pricing" className="text-muted-foreground hover:text-foreground transition-colors">
              Pricing
            </a>
          </div>
          <div className="flex items-center space-x-4">
            <Link href="/auth/login" className="btn-ghost">
              Sign In
            </Link>
            <Link href="/auth/register" className="btn-primary">
              Get Started
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="container mx-auto px-4 py-20 text-center">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-4xl md:text-6xl font-bold leading-tight mb-6">
            Transform Corporate{' '}
            <span className="gradient-text">Learning</span>{' '}
            with AI
          </h1>
          <p className="text-xl text-muted-foreground mb-8 max-w-2xl mx-auto">
            Revolutionize your organization's onboarding and knowledge sharing with 
            AI-powered learning experiences, gamification, and intelligent insights.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link href="/auth/register" className="btn-primary inline-flex items-center px-8 py-4 text-lg">
              Start Free Trial
              <ArrowRight className="ml-2 w-5 h-5" />
            </Link>
            <Link href="#demo" className="btn-outline inline-flex items-center px-8 py-4 text-lg">
              Watch Demo
            </Link>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="container mx-auto px-4 py-20">
        <div className="text-center mb-16">
          <h2 className="text-3xl font-bold mb-4">Powerful Features for Modern Learning</h2>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Everything you need to create engaging, effective corporate learning experiences.
          </p>
        </div>
        
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
          <FeatureCard
            icon={<Brain className="w-8 h-8" />}
            title="AI-Powered Learning"
            description="Personalized learning paths and intelligent content recommendations powered by advanced AI."
          />
          <FeatureCard
            icon={<Trophy className="w-8 h-8" />}
            title="Gamification"
            description="Boost engagement with XP points, badges, leaderboards, and achievement systems."
          />
          <FeatureCard
            icon={<BookOpen className="w-8 h-8" />}
            title="Interactive Courses"
            description="Rich multimedia content with videos, quizzes, assignments, and hands-on activities."
          />
          <FeatureCard
            icon={<MessageSquare className="w-8 h-8" />}
            title="Collaborative Forum"
            description="Foster knowledge sharing with Q&A forums and peer-to-peer learning."
          />
          <FeatureCard
            icon={<BarChart3 className="w-8 h-8" />}
            title="Advanced Analytics"
            description="Track progress, identify gaps, and measure learning effectiveness with detailed insights."
          />
          <FeatureCard
            icon={<Users className="w-8 h-8" />}
            title="Role-Based Access"
            description="Customized experiences for learners, SMEs, managers, and administrators."
          />
        </div>
      </section>

      {/* How It Works Section */}
      <section id="how-it-works" className="bg-muted/30 py-20">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold mb-4">How K-Orbit Works</h2>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              Simple steps to transform your corporate learning experience.
            </p>
          </div>
          
          <div className="grid md:grid-cols-3 gap-8">
            <StepCard
              step="1"
              title="Upload Content"
              description="SMEs upload training materials, documents, and resources. Our AI processes and organizes everything."
            />
            <StepCard
              step="2"
              title="AI Creates Courses"
              description="AI generates interactive courses, quizzes, and learning paths from your content automatically."
            />
            <StepCard
              step="3"
              title="Learners Engage"
              description="Employees access personalized learning experiences with gamification and real-time support."
            />
          </div>
        </div>
      </section>

      {/* Social Proof Section */}
      <section className="container mx-auto px-4 py-20">
        <div className="text-center mb-16">
          <h2 className="text-3xl font-bold mb-4">Trusted by Leading Organizations</h2>
          <p className="text-xl text-muted-foreground">
            Join thousands of companies already transforming their learning culture.
          </p>
        </div>
        
        <div className="grid md:grid-cols-3 gap-8">
          <MetricCard
            value="98%"
            label="Employee Engagement"
            description="Higher engagement rates compared to traditional training"
          />
          <MetricCard
            value="75%"
            label="Faster Onboarding"
            description="Reduce time-to-productivity for new hires"
          />
          <MetricCard
            value="60%"
            label="Cost Reduction"
            description="Lower training costs while improving outcomes"
          />
        </div>
      </section>

      {/* CTA Section */}
      <section className="bg-gradient-to-r from-primary to-secondary py-20">
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-3xl font-bold text-white mb-4">
            Ready to Transform Your Learning?
          </h2>
          <p className="text-xl text-primary-foreground/80 mb-8 max-w-2xl mx-auto">
            Start your free trial today and see the difference AI-powered learning can make.
          </p>
          <Link href="/auth/register" className="btn-secondary inline-flex items-center px-8 py-4 text-lg">
            Get Started Now
            <ArrowRight className="ml-2 w-5 h-5" />
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-muted/50 py-12">
        <div className="container mx-auto px-4">
          <div className="grid md:grid-cols-4 gap-8">
            <div>
              <div className="flex items-center space-x-2 mb-4">
                <div className="w-6 h-6 bg-gradient-to-br from-primary to-secondary rounded">
                  <Brain className="w-4 h-4 text-white m-1" />
                </div>
                <span className="font-bold">K-Orbit</span>
              </div>
              <p className="text-muted-foreground">
                AI-powered corporate learning platform for the modern workplace.
              </p>
            </div>
            <div>
              <h3 className="font-semibold mb-4">Product</h3>
              <ul className="space-y-2 text-muted-foreground">
                <li><a href="#" className="hover:text-foreground">Features</a></li>
                <li><a href="#" className="hover:text-foreground">Pricing</a></li>
                <li><a href="#" className="hover:text-foreground">Enterprise</a></li>
                <li><a href="#" className="hover:text-foreground">Security</a></li>
              </ul>
            </div>
            <div>
              <h3 className="font-semibold mb-4">Resources</h3>
              <ul className="space-y-2 text-muted-foreground">
                <li><a href="#" className="hover:text-foreground">Documentation</a></li>
                <li><a href="#" className="hover:text-foreground">Blog</a></li>
                <li><a href="#" className="hover:text-foreground">Case Studies</a></li>
                <li><a href="#" className="hover:text-foreground">Support</a></li>
              </ul>
            </div>
            <div>
              <h3 className="font-semibold mb-4">Company</h3>
              <ul className="space-y-2 text-muted-foreground">
                <li><a href="#" className="hover:text-foreground">About</a></li>
                <li><a href="#" className="hover:text-foreground">Careers</a></li>
                <li><a href="#" className="hover:text-foreground">Privacy</a></li>
                <li><a href="#" className="hover:text-foreground">Terms</a></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-border mt-8 pt-8 text-center text-muted-foreground">
            <p>&copy; 2024 K-Orbit. All rights reserved.</p>
          </div>
        </div>
      </footer>
      </div>
    </div>
  );
}

interface FeatureCardProps {
  icon: ReactNode;
  title: string;
  description: string;
}

function FeatureCard({ icon, title, description }: FeatureCardProps) {
  return (
    <div className="glass-card p-6 text-center hover:scale-105 transition-all duration-300 group">
      <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-primary/20 to-secondary/20 backdrop-blur-sm text-primary rounded-xl mb-4 group-hover:shadow-lg transition-shadow">
        {icon}
      </div>
      <h3 className="text-xl font-semibold mb-2 text-foreground">{title}</h3>
      <p className="text-muted-foreground">{description}</p>
    </div>
  );
}

interface StepCardProps {
  step: string;
  title: string;
  description: string;
}

function StepCard({ step, title, description }: StepCardProps) {
  return (
    <div className="text-center">
      <div className="inline-flex items-center justify-center w-12 h-12 bg-primary text-primary-foreground rounded-full text-xl font-bold mb-4">
        {step}
      </div>
      <h3 className="text-xl font-semibold mb-2">{title}</h3>
      <p className="text-muted-foreground">{description}</p>
    </div>
  );
}

interface MetricCardProps {
  value: string;
  label: string;
  description: string;
}

function MetricCard({ value, label, description }: MetricCardProps) {
  return (
    <div className="text-center">
      <div className="text-4xl font-bold text-primary mb-2">{value}</div>
      <div className="text-xl font-semibold mb-2">{label}</div>
      <p className="text-muted-foreground">{description}</p>
    </div>
  );
} 