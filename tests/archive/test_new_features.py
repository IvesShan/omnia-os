#!/usr/bin/env python3
"""
Test script for new Omnia features:
1. Workflow Engine
2. Vector Store (semantic search)
3. Self-Evolution Engine
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

print("=" * 60)
print("Omnia 2.0 Feature Test")
print("=" * 60)


def test_workflow_engine():
    """Test Workflow Engine"""
    print("\n📋 Testing Workflow Engine...")
    
    try:
        from core.orchestration import WorkflowEngine, WorkflowStep, WorkflowContext
        
        # Create a simple workflow
        async def step1(context: WorkflowContext):
            print("  [Step 1] Analyzing...")
            context.set("analysis", "completed")
            return {"status": "analyzed"}
        
        async def step2(context: WorkflowContext):
            print("  [Step 2] Processing...")
            return {"status": "processed"}
        
        async def step3(context: WorkflowContext):
            print("  [Step 3] Finalizing...")
            return {"status": "finalized"}
        
        workflow = [
            WorkflowStep(name="analyze", action=step1, description="Analyze task"),
            WorkflowStep(name="process", action=step2, depends_on=["analyze"], description="Process task"),
            WorkflowStep(name="finalize", action=step3, depends_on=["process"], description="Finalize task"),
        ]
        
        engine = WorkflowEngine()
        
        # Run workflow
        async def run():
            result = await engine.run(workflow, inputs={"task": "test"})
            return result
        
        result = asyncio.run(run())
        
        print(f"  ✅ Workflow completed: {result.success}")
        print(f"  ✅ Duration: {result.duration_ms:.2f}ms")
        print(f"  ✅ Steps: {len(result.step_results)}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_vector_store():
    """Test Vector Store"""
    print("\n🔍 Testing Vector Store (Semantic Search)...")
    
    try:
        from core.neural_graph import VectorStore
        
        # Create vector store
        store = VectorStore()
        
        # Add some test memories
        print("  Adding test memories...")
        store.add_memory(
            memory_id="test_001",
            text="用户喜欢使用深色主题进行编程",
            metadata={"layer": "habits", "category": "preferences"}
        )
        store.add_memory(
            memory_id="test_002",
            text="Omnia 项目是一个 AI 操作系统",
            metadata={"layer": "facts", "category": "project"}
        )
        store.add_memory(
            memory_id="test_003",
            text="用户经常在晚上工作，偏好夜间模式",
            metadata={"layer": "habits", "category": "work_style"}
        )
        
        print(f"  ✅ Added {store.count()} memories")
        
        # Test semantic search
        print("  Testing semantic search...")
        results = store.search("用户偏好", top_k=3)
        
        print(f"  ✅ Found {len(results)} results:")
        for i, r in enumerate(results, 1):
            print(f"    {i}. [{r.score:.3f}] {r.text[:50]}...")
        
        # Cleanup
        store.delete_memory("test_001")
        store.delete_memory("test_002")
        store.delete_memory("test_003")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_self_evolution():
    """Test Self-Evolution Engine"""
    print("\n🧬 Testing Self-Evolution Engine...")
    
    try:
        from core.skill_forge import SelfEvolutionEngine
        from core.feature.flags import FeatureFlags as FF
        
        # Check if feature flag exists
        print(f"  Feature flag 'EXPERIMENTAL_SELF_EVOLUTION' exists: {FF.is_defined('EXPERIMENTAL_SELF_EVOLUTION')}")
        print(f"  Current state: {FF.is_enabled('EXPERIMENTAL_SELF_EVOLUTION')}")
        
        # Enable the feature
        print("  Enabling self-evolution...")
        FF.enable("EXPERIMENTAL_SELF_EVOLUTION")
        print(f"  ✅ Enabled: {FF.is_enabled('EXPERIMENTAL_SELF_EVOLUTION')}")
        
        # Create engine
        engine = SelfEvolutionEngine()
        
        print(f"  ✅ Self-evolution engine created")
        print(f"  ✅ Is enabled: {engine.is_enabled()}")
        
        # Get stats
        stats = engine.get_stats()
        print(f"  ✅ Stats: {stats.to_dict()}")
        
        # Disable for now (to avoid actual execution)
        FF.disable("EXPERIMENTAL_SELF_EVOLUTION")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_feature_flags():
    """Test Feature Flags"""
    print("\n🚩 Testing Feature Flags...")
    
    try:
        from core.feature.flags import FeatureFlags as FF, FeatureCategory
        
        # List some flags
        print("  Experimental flags:")
        experimental = FF.list_by_category(FeatureCategory.EXPERIMENTAL)
        for name, enabled in list(experimental.items())[:5]:
            status = "✅" if enabled else "❌"
            print(f"    {status} {name}")
        
        print(f"\n  Total flags: {len(FF.list_all())}")
        print(f"  Enabled: {len(FF.list_enabled())}")
        print(f"  Disabled: {len(FF.list_disabled())}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    results = {
        "Feature Flags": test_feature_flags(),
        "Workflow Engine": test_workflow_engine(),
        "Vector Store": test_vector_store(),
        "Self-Evolution": test_self_evolution(),
    }
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {name}: {status}")
    
    total = len(results)
    passed = sum(results.values())
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    return all(results.values())


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
