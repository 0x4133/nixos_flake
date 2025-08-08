# API Caller - Visual API Workflow Builder

A powerful React + TypeScript SPA that lets you visually chain arbitrary REST/GraphQL API calls in any order and feed outputs from earlier calls into later ones. Built with React Flow for intuitive node-based workflow design.

## 🚀 Features

### Core Functionality
- **Visual Node Editor**: Drag-and-drop interface using React Flow
- **API Call Nodes**: Configurable HTTP methods, URLs, headers, and body
- **Transform Nodes**: JavaScript expressions with lodash/fp support
- **Output Nodes**: Pretty-printed JSON with Monaco Editor
- **Data Wiring**: Connect nodes to pass data between API calls
- **Variable Interpolation**: Use `{{path.to.value}}` syntax in API configurations

### Execution Engine
- **Topological Sorting**: Automatic dependency resolution
- **Cycle Detection**: Prevents infinite loops
- **Real-time Status**: Live updates during execution
- **Error Handling**: Graceful error recovery and detailed logging
- **Async Support**: Full async/await support for complex workflows

### User Experience
- **Dark/Light Theme**: Toggle between themes
- **Keyboard Shortcuts**: ⌘/Ctrl+S to save, ⌘/Ctrl+R to run
- **Mini-map & Zoom**: Navigate large workflows easily
- **Auto-save**: Automatic localStorage persistence
- **Import/Export**: JSON-based project sharing

### Security & Robustness
- **Safe JavaScript Evaluation**: Restricted execution environment
- **CORS Proxy Support**: Configurable proxy for cross-origin requests
- **HTTPS Enforcement**: Secure by default
- **Input Validation**: Comprehensive validation and sanitization

## 🛠️ Tech Stack

- **Frontend**: React 18 + TypeScript
- **Build Tool**: Vite
- **State Management**: Zustand with persistence
- **UI Framework**: Tailwind CSS + DaisyUI
- **Flow Editor**: React Flow
- **Code Editor**: Monaco Editor
- **HTTP Client**: Axios
- **Testing**: Vitest + React Testing Library
- **E2E Testing**: Playwright

## 📦 Installation

### Prerequisites
- Node.js 20+ 
- npm or yarn

### Setup
```bash
# Clone the repository
git clone <repository-url>
cd api_caller

# Install dependencies
npm install

# Start development server
npm run dev
```

The application will be available at `http://localhost:3000`

## 🎯 Usage

### Getting Started
1. **Create a Project**: A default project is created automatically
2. **Add Nodes**: Drag nodes from the palette to the canvas
3. **Configure Nodes**: Click on nodes to expand and configure them
4. **Connect Nodes**: Drag from output handles to input handles
5. **Run Workflow**: Press ⌘R or click "Run Graph"

### Node Types

#### API Call Node
- **Purpose**: Make HTTP requests to APIs
- **Configuration**:
  - HTTP Method (GET, POST, PUT, DELETE, PATCH)
  - URL with variable interpolation
  - Headers (JSON format)
  - Request Body (for non-GET requests)
  - CORS Proxy toggle

#### Transform Node
- **Purpose**: Transform data using JavaScript expressions
- **Features**:
  - Access to lodash/fp functions via `_`
  - Built-in JavaScript globals (Math, JSON, Array, etc.)
  - Input data available as `data` variable
  - Safe execution environment

#### Output Node
- **Purpose**: Display final results
- **Features**:
  - Monaco Editor for syntax highlighting
  - JSON formatting
  - Expandable view

### Variable Interpolation
Use `{{path.to.value}}` syntax in API node configurations:

```json
{
  "url": "https://api.example.com/users/{{data.userId}}",
  "headers": {
    "Authorization": "Bearer {{data.token}}"
  },
  "body": "{\"name\": \"{{data.userName}}\"}"
}
```

### Transform Expressions
Examples of valid transform expressions:

```javascript
// Map array items
_.map(data, item => item.name)

// Filter data
_.filter(data, item => item.active)

// Transform objects
data.map(item => ({ ...item, processed: true }))

// Access nested properties
_.get(data, 'user.profile.email', 'unknown')

// Mathematical operations
Math.max(...data.map(item => item.value))
```

## 🧪 Testing

### Unit Tests
```bash
npm run test
```

### E2E Tests
```bash
npm run test:e2e
```

### Test Coverage
```bash
npm run test:coverage
```

## 🏗️ Build

### Development Build
```bash
npm run build:dev
```

### Production Build
```bash
npm run build
```

### Preview Production Build
```bash
npm run preview
```

## 🐳 Docker

### Build Image
```bash
docker build -t api-caller .
```

### Run Container
```bash
docker run -p 3000:3000 api-caller
```

## 📁 Project Structure

```
src/
├── components/          # React components
│   ├── nodes/          # Node type components
│   ├── Flow.tsx        # Main flow editor
│   ├── NodePalette.tsx # Node palette sidebar
│   └── ExecutionPanel.tsx # Execution logs panel
├── store/              # Zustand state management
├── types/              # TypeScript type definitions
├── utils/              # Utility functions
│   ├── execution.ts    # Graph execution engine
│   ├── nodes.ts        # Node execution logic
│   ├── interpolation.ts # Variable interpolation
│   └── safeEval.ts     # Safe JavaScript evaluation
└── test/               # Test setup and utilities
```

## 🔧 Configuration

### Environment Variables
- `VITE_API_BASE_URL`: Base URL for API calls
- `VITE_CORS_PROXY`: CORS proxy endpoint
- `VITE_ENABLE_ANALYTICS`: Enable usage analytics

### Customization
- **Themes**: Modify `tailwind.config.js` for custom themes
- **Node Types**: Add new node types in `src/components/nodes/`
- **Execution Logic**: Extend `src/utils/execution.ts`
- **Validation**: Customize validation in `src/utils/safeEval.ts`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/your-repo/api-caller/issues)
- **Documentation**: [Wiki](https://github.com/your-repo/api-caller/wiki)
- **Discussions**: [GitHub Discussions](https://github.com/your-repo/api-caller/discussions)

## 🗺️ Roadmap

- [ ] Swagger/OpenAPI import
- [ ] GraphQL support
- [ ] Authentication flows
- [ ] Rate limiting UI
- [ ] Advanced error handling
- [ ] Performance optimizations
- [ ] Plugin system
- [ ] Cloud deployment
