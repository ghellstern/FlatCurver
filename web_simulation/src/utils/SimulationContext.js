import React, { Component } from "react";

const SimulationContext = React.createContext();

export const withSimulation = Component => {
  const WrappedComponent = props => (
    <SimulationContext.Consumer>
      {context => <Component {...props} simulation={context} />}
    </SimulationContext.Consumer>
  );

  WrappedComponent.displayName = `withSimulation(${Component.displayName ||
    Component.name ||
    "Component"})`;

  return WrappedComponent;
};

// this is the main component, it has to be added at the root of the app.
// all components that use withSimulation(...) will have access to it via this.props.Simulation...
class SimulationProvider extends Component {
  constructor(props) {
    super(props);
    this.state = {
      show: false
    };
  }

  show() {
    this.setState({ show: true });
  }

  hide() {
    this.setState({ show: false });
  }

  load(func) {
    this.setState({ show: true });
    setTimeout(() => {
      func();
      this.setState({ show: false });
    }, 0);
  }

  render() {
    return (
      <SimulationContext.Provider
        value={{
          show: () => this.show(),
          hide: () => this.hide(),
          load: callback => this.load(callback)
        }}
      >
        {this.props.children}
      </SimulationContext.Provider>
    );
  }
}

export default SimulationProvider;
