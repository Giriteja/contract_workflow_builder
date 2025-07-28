import streamlit as st
import json
import uuid
from typing import Dict, List, Any
import pandas as pd
from datetime import datetime
import io

# Configure page
st.set_page_config(
    page_title="Workflow Builder",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for drag and drop styling
st.markdown("""
<style>
.workflow-canvas {
    background: linear-gradient(90deg, #f0f2f6 1px, transparent 1px),
                linear-gradient(#f0f2f6 1px, transparent 1px);
    background-size: 20px 20px;
    border: 2px dashed #ddd;
    border-radius: 10px;
    min-height: 600px;
    padding: 20px;
    margin: 10px 0;
}

.workflow-element {
    background: white;
    border: 2px solid #e1e5e9;
    border-radius: 8px;
    padding: 15px;
    margin: 10px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    cursor: move;
    transition: all 0.3s ease;
}

.workflow-element:hover {
    border-color: #ff4b4b;
    box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    transform: translateY(-2px);
}

.element-palette {
    background: #f8f9fa;
    border-radius: 10px;
    padding: 15px;
    margin-bottom: 20px;
}

.element-button {
    display: block;
    width: 100%;
    padding: 10px;
    margin: 5px 0;
    background: white;
    border: 1px solid #ddd;
    border-radius: 5px;
    cursor: pointer;
    text-align: center;
    transition: all 0.2s ease;
}

.element-button:hover {
    background: #ff4b4b;
    color: white;
    border-color: #ff4b4b;
}

.workflow-connector {
    height: 2px;
    background: #ff4b4b;
    margin: 10px 0;
    border-radius: 2px;
}

.status-indicator {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    margin-right: 8px;
}

.status-ready { background-color: #28a745; }
.status-processing { background-color: #ffc107; }
.status-error { background-color: #dc3545; }
.status-pending { background-color: #6c757d; }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'workflow_elements' not in st.session_state:
    st.session_state.workflow_elements = []
if 'workflow_data' not in st.session_state:
    st.session_state.workflow_data = {}
if 'execution_results' not in st.session_state:
    st.session_state.execution_results = {}

class WorkflowElement:
    def __init__(self, element_type: str, element_id: str = None):
        self.id = element_id or str(uuid.uuid4())
        self.type = element_type
        self.position = {'x': 0, 'y': 0}
        self.config = {}
        self.status = 'pending'
        self.output = None
        
    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'position': self.position,
            'config': self.config,
            'status': self.status,
            'output': self.output
        }

def create_element_palette():
    """Create the element palette sidebar"""
    st.sidebar.header("🧰 Element Palette")
    
    element_types = {
        "📄 PDF Upload": "pdf_upload",
        "📝 Text Input": "text_input",
        "🔢 Number Input": "number_input",
        "📅 Date Input": "date_input",
        "☑️ Checkbox": "checkbox",
        "🎛️ Slider": "slider",
        "📋 Select Box": "selectbox",
        "🔀 Conditional": "conditional",
        "🔄 Loop": "loop",
        "📊 Data Display": "data_display",
        "📈 Chart": "chart",
        "💾 Save Data": "save_data",
        "🔗 API Call": "api_call",
        "📧 Email": "email",
        "⏱️ Timer": "timer"
    }
    
    st.sidebar.markdown("**Click to add elements to workflow:**")
    
    for display_name, element_type in element_types.items():
        if st.sidebar.button(display_name, key=f"add_{element_type}"):
            add_element_to_workflow(element_type)
    
    st.sidebar.markdown("---")
    
    # Workflow actions
    st.sidebar.header("⚡ Workflow Actions")
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("▶️ Run", key="run_workflow"):
            execute_workflow()
    with col2:
        if st.button("🗑️ Clear", key="clear_workflow"):
            st.session_state.workflow_elements = []
            st.session_state.workflow_data = {}
            st.session_state.execution_results = {}
            st.rerun()
    
    if st.sidebar.button("💾 Export", key="export_workflow"):
        export_workflow()
    
    uploaded_file = st.sidebar.file_uploader("📥 Import Workflow", type=['json'])
    if uploaded_file:
        import_workflow(uploaded_file)

def add_element_to_workflow(element_type: str):
    """Add a new element to the workflow"""
    element = WorkflowElement(element_type)
    element.position = {'x': len(st.session_state.workflow_elements) * 100, 'y': 50}
    st.session_state.workflow_elements.append(element)
    st.rerun()

def render_workflow_canvas():
    """Render the main workflow canvas"""
    st.header("🔧 Workflow Builder")
    
    if not st.session_state.workflow_elements:
        st.markdown("""
        <div class="workflow-canvas">
            <div style="text-align: center; color: #666; margin-top: 200px;">
                <h3>👋 Welcome to Workflow Builder!</h3>
                <p>Start by adding elements from the sidebar to create your workflow.</p>
                <p>Elements will appear here and can be configured individually.</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        with st.container():
            st.markdown('<div class="workflow-canvas">', unsafe_allow_html=True)
            
            for i, element in enumerate(st.session_state.workflow_elements):
                render_workflow_element(element, i)
                
                # Add connector between elements (except for the last one)
                if i < len(st.session_state.workflow_elements) - 1:
                    st.markdown('<div class="workflow-connector"></div>', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)

def render_workflow_element(element: WorkflowElement, index: int):
    """Render individual workflow element"""
    status_colors = {
        'pending': 'status-pending',
        'ready': 'status-ready',
        'processing': 'status-processing',
        'error': 'status-error'
    }
    
    with st.container():
        col1, col2, col3 = st.columns([0.1, 0.8, 0.1])
        
        with col2:
            st.markdown(f"""
            <div class="workflow-element">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <h4>🔧 {get_element_display_name(element.type)}</h4>
                    <span class="status-indicator {status_colors.get(element.status, 'status-pending')}"></span>
                </div>
            """, unsafe_allow_html=True)
            
            # Render element-specific configuration
            render_element_config(element, index)
            
            # Element actions
            col_config, col_delete = st.columns([3, 1])
            with col_delete:
                if st.button("🗑️", key=f"delete_{element.id}", help="Delete element"):
                    st.session_state.workflow_elements.pop(index)
                    st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)

def get_element_display_name(element_type: str) -> str:
    """Get display name for element type"""
    names = {
        'pdf_upload': 'PDF Upload',
        'text_input': 'Text Input',
        'number_input': 'Number Input',
        'date_input': 'Date Input',
        'checkbox': 'Checkbox',
        'slider': 'Slider',
        'selectbox': 'Select Box',
        'conditional': 'Conditional Logic',
        'loop': 'Loop',
        'data_display': 'Data Display',
        'chart': 'Chart',
        'save_data': 'Save Data',
        'api_call': 'API Call',
        'email': 'Email',
        'timer': 'Timer'
    }
    return names.get(element_type, element_type.title())

def render_element_config(element: WorkflowElement, index: int):
    """Render configuration for specific element types"""
    
    if element.type == 'pdf_upload':
        st.write("📄 **PDF Upload Configuration**")
        uploaded_file = st.file_uploader(
            "Choose PDF file", 
            type=['pdf'], 
            key=f"pdf_{element.id}"
        )
        if uploaded_file:
            element.config['filename'] = uploaded_file.name
            element.config['size'] = uploaded_file.size
            element.status = 'ready'
            st.success(f"PDF uploaded: {uploaded_file.name}")
    
    elif element.type == 'text_input':
        st.write("📝 **Text Input Configuration**")
        label = st.text_input("Label", value="Enter text", key=f"label_{element.id}")
        value = st.text_area("Input Text", key=f"text_{element.id}")
        element.config = {'label': label, 'value': value}
        if value:
            element.status = 'ready'
    
    elif element.type == 'number_input':
        st.write("🔢 **Number Input Configuration**")
        label = st.text_input("Label", value="Enter number", key=f"num_label_{element.id}")
        value = st.number_input(label, key=f"number_{element.id}")
        element.config = {'label': label, 'value': value}
        element.status = 'ready'
    
    elif element.type == 'date_input':
        st.write("📅 **Date Input Configuration**")
        label = st.text_input("Label", value="Select date", key=f"date_label_{element.id}")
        value = st.date_input(label, key=f"date_{element.id}")
        element.config = {'label': label, 'value': str(value)}
        element.status = 'ready'
    
    elif element.type == 'checkbox':
        st.write("☑️ **Checkbox Configuration**")
        label = st.text_input("Label", value="Check option", key=f"cb_label_{element.id}")
        value = st.checkbox(label, key=f"checkbox_{element.id}")
        element.config = {'label': label, 'value': value}
        element.status = 'ready'
    
    elif element.type == 'slider':
        st.write("🎛️ **Slider Configuration**")
        label = st.text_input("Label", value="Select value", key=f"slider_label_{element.id}")
        min_val = st.number_input("Min Value", value=0, key=f"slider_min_{element.id}")
        max_val = st.number_input("Max Value", value=100, key=f"slider_max_{element.id}")
        value = st.slider(label, min_value=int(min_val), max_value=int(max_val), key=f"slider_{element.id}")
        element.config = {'label': label, 'min': min_val, 'max': max_val, 'value': value}
        element.status = 'ready'
    
    elif element.type == 'selectbox':
        st.write("📋 **Select Box Configuration**")
        label = st.text_input("Label", value="Choose option", key=f"sb_label_{element.id}")
        options_text = st.text_area("Options (one per line)", value="Option 1\nOption 2\nOption 3", key=f"sb_options_{element.id}")
        options = [opt.strip() for opt in options_text.split('\n') if opt.strip()]
        if options:
            value = st.selectbox(label, options, key=f"selectbox_{element.id}")
            element.config = {'label': label, 'options': options, 'value': value}
            element.status = 'ready'
    
    elif element.type == 'conditional':
        st.write("🔀 **Conditional Logic Configuration**")
        condition_type = st.selectbox("Condition Type", ["equals", "greater_than", "less_than", "contains"], key=f"cond_type_{element.id}")
        condition_value = st.text_input("Condition Value", key=f"cond_val_{element.id}")
        true_action = st.text_input("Action if True", key=f"true_action_{element.id}")
        false_action = st.text_input("Action if False", key=f"false_action_{element.id}")
        element.config = {
            'condition_type': condition_type,
            'condition_value': condition_value,
            'true_action': true_action,
            'false_action': false_action
        }
        element.status = 'ready' if condition_value else 'pending'
    
    elif element.type == 'data_display':
        st.write("📊 **Data Display Configuration**")
        display_type = st.selectbox("Display Type", ["table", "json", "text"], key=f"display_type_{element.id}")
        element.config = {'display_type': display_type}
        element.status = 'ready'
        
        # Show sample data
        if display_type == "table":
            sample_data = pd.DataFrame({
                'Column 1': [1, 2, 3],
                'Column 2': ['A', 'B', 'C'],
                'Column 3': [True, False, True]
            })
            st.dataframe(sample_data)
    
    elif element.type == 'chart':
        st.write("📈 **Chart Configuration**")
        chart_type = st.selectbox("Chart Type", ["line", "bar", "scatter", "area"], key=f"chart_type_{element.id}")
        element.config = {'chart_type': chart_type}
        element.status = 'ready'
    
    elif element.type == 'api_call':
        st.write("🔗 **API Call Configuration**")
        url = st.text_input("API URL", key=f"api_url_{element.id}")
        method = st.selectbox("Method", ["GET", "POST", "PUT", "DELETE"], key=f"api_method_{element.id}")
        headers = st.text_area("Headers (JSON format)", value="{}", key=f"api_headers_{element.id}")
        element.config = {'url': url, 'method': method, 'headers': headers}
        element.status = 'ready' if url else 'pending'
    
    elif element.type == 'email':
        st.write("📧 **Email Configuration**")
        recipient = st.text_input("Recipient Email", key=f"email_to_{element.id}")
        subject = st.text_input("Subject", key=f"email_subject_{element.id}")
        body = st.text_area("Email Body", key=f"email_body_{element.id}")
        element.config = {'recipient': recipient, 'subject': subject, 'body': body}
        element.status = 'ready' if recipient and subject else 'pending'
    
    else:
        st.write(f"**{get_element_display_name(element.type)} Configuration**")
        st.info("Configuration options for this element type coming soon!")

def execute_workflow():
    """Execute the workflow"""
    if not st.session_state.workflow_elements:
        st.warning("No workflow elements to execute!")
        return
    
    st.info("🚀 Executing workflow...")
    
    results = {}
    
    for i, element in enumerate(st.session_state.workflow_elements):
        element.status = 'processing'
        
        try:
            # Simulate processing time
            import time
            time.sleep(0.5)
            
            # Execute element based on type
            if element.type == 'pdf_upload':
                if 'filename' in element.config:
                    results[element.id] = f"PDF processed: {element.config['filename']}"
                    element.status = 'ready'
                else:
                    element.status = 'error'
                    results[element.id] = "No PDF uploaded"
            
            elif element.type in ['text_input', 'number_input', 'date_input', 'checkbox', 'slider', 'selectbox']:
                results[element.id] = element.config.get('value', 'No value')
                element.status = 'ready'
            
            elif element.type == 'conditional':
                condition_met = True  # Simplified logic
                action = element.config['true_action'] if condition_met else element.config['false_action']
                results[element.id] = f"Executed: {action}"
                element.status = 'ready'
            
            elif element.type == 'data_display':
                results[element.id] = "Data displayed successfully"
                element.status = 'ready'
            
            elif element.type == 'api_call':
                results[element.id] = f"API call to {element.config.get('url', 'undefined')} completed"
                element.status = 'ready'
            
            elif element.type == 'email':
                results[element.id] = f"Email sent to {element.config.get('recipient', 'undefined')}"
                element.status = 'ready'
            
            else:
                results[element.id] = f"{element.type} executed successfully"
                element.status = 'ready'
                
        except Exception as e:
            element.status = 'error'
            results[element.id] = f"Error: {str(e)}"
    
    st.session_state.execution_results = results
    st.success("✅ Workflow execution completed!")
    
    # Show results
    with st.expander("📋 Execution Results", expanded=True):
        for element_id, result in results.items():
            element = next((e for e in st.session_state.workflow_elements if e.id == element_id), None)
            if element:
                status_emoji = "✅" if element.status == 'ready' else "❌" if element.status == 'error' else "⏳"
                st.write(f"{status_emoji} **{get_element_display_name(element.type)}**: {result}")

def export_workflow():
    """Export workflow to JSON"""
    workflow_data = {
        'elements': [element.to_dict() for element in st.session_state.workflow_elements],
        'created_at': datetime.now().isoformat(),
        'version': '1.0'
    }
    
    json_str = json.dumps(workflow_data, indent=2)
    st.download_button(
        label="📥 Download Workflow JSON",
        data=json_str,
        file_name=f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json"
    )

def import_workflow(uploaded_file):
    """Import workflow from JSON"""
    try:
        workflow_data = json.load(uploaded_file)
        
        # Clear existing workflow
        st.session_state.workflow_elements = []
        
        # Load elements
        for element_data in workflow_data.get('elements', []):
            element = WorkflowElement(element_data['type'], element_data['id'])
            element.position = element_data.get('position', {'x': 0, 'y': 0})
            element.config = element_data.get('config', {})
            element.status = element_data.get('status', 'pending')
            element.output = element_data.get('output')
            st.session_state.workflow_elements.append(element)
        
        st.success(f"✅ Workflow imported successfully! Loaded {len(st.session_state.workflow_elements)} elements.")
        st.rerun()
        
    except Exception as e:
        st.error(f"❌ Error importing workflow: {str(e)}")

def main():
    """Main application function"""
    # Create sidebar palette
    create_element_palette()
    
    # Render main workflow canvas
    render_workflow_canvas()
    
    # Show workflow statistics
    if st.session_state.workflow_elements:
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)
        
        total_elements = len(st.session_state.workflow_elements)
        ready_elements = sum(1 for e in st.session_state.workflow_elements if e.status == 'ready')
        error_elements = sum(1 for e in st.session_state.workflow_elements if e.status == 'error')
        pending_elements = total_elements - ready_elements - error_elements
        
        with col1:
            st.metric("Total Elements", total_elements)
        with col2:
            st.metric("Ready", ready_elements)
        with col3:
            st.metric("Pending", pending_elements)
        with col4:
            st.metric("Errors", error_elements)

if __name__ == "__main__":
    main()
