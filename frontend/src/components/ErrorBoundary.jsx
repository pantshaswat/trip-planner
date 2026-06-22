import { Component } from 'react';

/**
 * Catches any render error in the output area so a malformed/unexpected
 * response can never blank the whole app. Shows a friendly message instead.
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { failed: false };
  }

  static getDerivedStateFromError() {
    return { failed: true };
  }

  // Reset the error when a new result comes in (resetKey changes).
  componentDidUpdate(prevProps) {
    if (this.state.failed && prevProps.resetKey !== this.props.resetKey) {
      this.setState({ failed: false });
    }
  }

  render() {
    if (this.state.failed) {
      return (
        <div className="alert alert-error" role="alert">
          Something went wrong displaying this trip. Please try again with
          different locations.
        </div>
      );
    }
    return this.props.children;
  }
}
