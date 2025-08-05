export default function TestStylingPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-8">
      <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-6">
        <h1 className="text-2xl font-bold text-gray-800 mb-4">Styling Test</h1>
        
        <div className="space-y-4">
          <button className="btn-primary w-full">Primary Button</button>
          <button className="btn-secondary w-full">Secondary Button</button>
          <button className="btn-outline w-full">Outline Button</button>
          
          <div className="p-4 bg-gradient-to-r from-primary to-secondary rounded-lg">
            <span className="text-white font-semibold">Gradient Background</span>
          </div>
          
          <div className="gradient-text text-xl font-bold">
            Gradient Text Test
          </div>
          
          <div className="card p-4">
            <h3 className="font-semibold mb-2">Card Component</h3>
            <p className="text-muted-foreground">This is a card with proper styling.</p>
          </div>
          
          <div className="badge-default inline-block">Default Badge</div>
          <div className="badge-secondary inline-block ml-2">Secondary Badge</div>
        </div>
      </div>
    </div>
  );
} 