import { useState, useRef } from "react";
import * as React from "react";
import { withAuthenticator } from "@aws-amplify/ui-react";
import "@aws-amplify/ui-react/styles.css";
import { AppLayout, SideNavigation } from '@cloudscape-design/components';
import TopNavigation from "@cloudscape-design/components/top-navigation";
import S2sChatBot from './s2s'


const App = ({ signOut, user }) => {
  const [displayTopMenu] = useState(window.self === window.top);

  return (
    <div>
      <S2sChatBot />
    </div>
  );
}
export default App;
