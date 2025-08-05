# Contributing to QuickResolve

Thank you for your interest in contributing to QuickResolve! This document provides guidelines and information for contributors.

## 🤝 How to Contribute

We welcome contributions from the community! Here are several ways you can contribute:

### 🐛 Reporting Bugs

- Use the GitHub issue tracker
- Include detailed steps to reproduce the bug
- Provide system information (OS, Docker version, etc.)
- Include error messages and logs when possible

### 💡 Suggesting Enhancements

- Use the GitHub issue tracker with the "enhancement" label
- Describe the feature and its benefits
- Include use cases and examples

### 🔧 Code Contributions

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes**
4. **Test thoroughly**
5. **Commit your changes**: `git commit -m 'Add amazing feature'`
6. **Push to the branch**: `git push origin feature/amazing-feature`
7. **Open a Pull Request**

## 🏗️ Development Setup

### Prerequisites

- Docker and Docker Compose
- Python 3.8+ (for local development)
- Git

### Local Development

1. **Clone your fork**:
   ```bash
   git clone https://github.com/chaners-com/quickresolve.git
   cd quickresolve
   ```

2. **Set up environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start services**:
   ```bash
   docker-compose up -d
   ```

4. **Run tests** (when available):
   ```bash
   # Add test commands here when tests are implemented
   ```

## 📝 Code Style Guidelines

### Python (FastAPI Services)

- Follow PEP 8 style guidelines
- Use type hints where possible
- Add docstrings to functions and classes
- Keep functions small and focused
- Use meaningful variable and function names

### JavaScript (Frontend)

- Use modern ES6+ syntax
- Follow consistent indentation (2 spaces)
- Use meaningful variable and function names
- Add comments for complex logic

### General Guidelines

- Write clear, descriptive commit messages
- Keep changes focused and atomic
- Add tests for new features
- Update documentation as needed

## 🧪 Testing

### Before Submitting

- [ ] Code runs without errors
- [ ] All existing functionality still works
- [ ] New features are tested
- [ ] Documentation is updated
- [ ] No sensitive data is committed

### Testing Checklist

- [ ] Test file upload functionality
- [ ] Test search functionality
- [ ] Test with different file types
- [ ] Test error handling
- [ ] Test API endpoints

## 📋 Pull Request Guidelines

### Before Submitting a PR

1. **Ensure your code follows the style guidelines**
2. **Add tests for new functionality**
3. **Update documentation if needed**
4. **Test your changes thoroughly**

### PR Description Template

```markdown
## Description
Brief description of the changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Refactoring

## Testing
- [ ] Tested locally
- [ ] Added unit tests
- [ ] Updated documentation

## Checklist
- [ ] My code follows the style guidelines
- [ ] I have tested my changes
- [ ] I have updated the documentation
- [ ] My changes generate no new warnings
```

## 🏷️ Issue Labels

We use the following labels to categorize issues:

- `bug` - Something isn't working
- `enhancement` - New feature or request
- `documentation` - Improvements or additions to documentation
- `good first issue` - Good for newcomers
- `help wanted` - Extra attention is needed
- `question` - Further information is requested

## 🚀 Release Process

1. **Create a release branch**: `git checkout -b release/v1.0.0`
2. **Update version numbers** in relevant files
3. **Update CHANGELOG.md** with new features and fixes
4. **Create a pull request** for the release
5. **Merge and tag** the release

## 📞 Getting Help

If you need help with contributing:

1. **Check existing issues** for similar questions
2. **Read the documentation** in the README
3. **Open a new issue** with the "question" label
4. **Join our discussions** (if available)

## 🎯 Areas for Contribution

We're particularly interested in contributions in these areas:

- **Testing**: Unit tests, integration tests, end-to-end tests
- **Documentation**: API documentation, user guides, tutorials
- **Performance**: Optimizations, caching, database improvements
- **Security**: Security audits, vulnerability fixes
- **UI/UX**: Frontend improvements, better user experience
- **Monitoring**: Logging, metrics, health checks

## 📄 License

By contributing to QuickResolve, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to QuickResolve! 🚀 
