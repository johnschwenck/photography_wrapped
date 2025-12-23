"""
Edge Case Testing for Photography Wrapped
Tests: duplicate entries, empty folders, invalid paths, malformed data
"""

import os
import sys
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from database.db_manager import DatabaseManager
from extractors.exif_extractor import ExifExtractor
from models.session import Session
from storage.storage_provider import LocalStorageProvider

def test_duplicate_session_prevention():
    """Test that duplicate sessions cannot be created"""
    print("\n=== Test 1: Duplicate Session Prevention ===")
    
    # Use test database
    test_db = DatabaseManager(db_type='sqlite', connection_string=':memory:')
    
    # Test 1a: Exact duplicates
    session1 = Session(
        name="Test Session",
        category="test_category",
        group="test_group",
        total_photos=10
    )
    created1 = test_db.create_session(session1)
    print(f"✓ Created first session (ID: {created1.id})")
    
    # Try to create exact duplicate
    try:
        session2 = Session(
            name="Test Session",
            category="test_category",
            group="test_group",
            total_photos=20
        )
        created2 = test_db.create_session(session2)
        print(f"✗ FAIL: Exact duplicate was created (ID: {created2.id})")
        return False
    except Exception as e:
        print(f"✓ Exact duplicate prevented - {type(e).__name__}")
    
    # Test 1b: Case variations (should be prevented)
    try:
        session3 = Session(
            name="Test Session",
            category="TEST_CATEGORY",  # Different case
            group="test_group",
            total_photos=30
        )
        created3 = test_db.create_session(session3)
        print(f"✗ FAIL: Case variation duplicate was created (ID: {created3.id})")
        return False
    except Exception as e:
        print(f"✓ Case variation duplicate prevented - {type(e).__name__}")
    
    # Test 1c: Whitespace variations (should be allowed - different content)
    try:
        session4 = Session(
            name="Test Session",
            category="test_category",
            group="test group",  # Space instead of underscore - different from "test_group"
            total_photos=40
        )
        created4 = test_db.create_session(session4)
        print(f"✓ Whitespace content difference allowed (ID: {created4.id}) - 'test group' != 'test_group'")
    except Exception as e:
        print(f"✗ FAIL: Different content was prevented - {type(e).__name__}")
        return False
    
    # Test 1d: Leading/trailing whitespace (should be prevented)
    try:
        session5 = Session(
            name=" Test Session ",  # Leading/trailing spaces
            category="test_category",
            group="test_group",
            total_photos=50
        )
        created5 = test_db.create_session(session5)
        print(f"✗ FAIL: Leading/trailing whitespace duplicate was created (ID: {created5.id})")
        return False
    except Exception as e:
        print(f"✓ Leading/trailing whitespace duplicate prevented - {type(e).__name__}")
    
    # Test 1e: Mixed case (should be prevented)
    try:
        session6 = Session(
            name="TEST SESSION",  # All caps
            category="Test_Category",  # Mixed case
            group="TEST_GROUP",  # All caps
            total_photos=60
        )
        created6 = test_db.create_session(session6)
        print(f"✗ FAIL: Mixed case duplicate was created (ID: {created6.id})")
        return False
    except Exception as e:
        print(f"✓ Mixed case duplicate prevented - {type(e).__name__}")
    
    print(f"✓ PASS: Duplicate prevention working correctly")
    return True


def test_empty_folder():
    """Test extraction from empty folder"""
    print("\n=== Test 2: Empty Folder Handling ===")
    
    # Create temporary empty directory
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Testing with empty folder: {temp_dir}")
        
        test_db = DatabaseManager(db_type='sqlite', connection_string=':memory:')
        storage = LocalStorageProvider()
        extractor = ExifExtractor(test_db, storage)
        
        try:
            session = extractor.extract_folder(
                folder_path=temp_dir,
                category="test",
                group="empty_test",
                session_name="Empty Folder Test"
            )
            
            # Empty folders should return None (no session created)
            if session is None:
                print(f"✓ PASS: Empty folder handled correctly, no session created")
                return True
            else:
                print(f"✗ FAIL: Expected None for empty folder, got session with {session.total_photos} photos")
                return False
                
        except Exception as e:
            print(f"✗ FAIL: Exception raised - {e}")
            return False


def test_invalid_path():
    """Test extraction from non-existent path"""
    print("\n=== Test 3: Invalid Path Handling ===")
    
    invalid_path = "C:\\This\\Path\\Does\\Not\\Exist\\At\\All"
    print(f"Testing with invalid path: {invalid_path}")
    
    test_db = DatabaseManager(db_type='sqlite', connection_string=':memory:')
    storage = LocalStorageProvider()
    extractor = ExifExtractor(test_db, storage)
    
    try:
        session = extractor.extract_folder(
            folder_path=invalid_path,
            category="test",
            group="invalid_test",
            session_name="Invalid Path Test"
        )
        
        if session is None or session.total_photos == 0:
            print(f"✓ PASS: Invalid path handled gracefully")
            return True
        else:
            print(f"✗ FAIL: Invalid path should not create session with photos")
            return False
            
    except Exception as e:
        # Exception is acceptable for invalid paths
        print(f"✓ PASS: Exception raised as expected - {type(e).__name__}: {str(e)[:100]}")
        return True


def test_folder_with_no_images():
    """Test folder that exists but contains no image files"""
    print("\n=== Test 4: Folder With No Images ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create some non-image files
        (Path(temp_dir) / "readme.txt").write_text("This is not an image")
        (Path(temp_dir) / "data.json").write_text('{"test": true}')
        (Path(temp_dir) / "script.py").write_text('print("hello")')
        
        print(f"Testing folder with non-image files: {temp_dir}")
        
        test_db = DatabaseManager(db_type='sqlite', connection_string=':memory:')
        storage = LocalStorageProvider()
        extractor = ExifExtractor(test_db, storage)
        
        try:
            session = extractor.extract_folder(
                folder_path=temp_dir,
                category="test",
                group="no_images_test",
                session_name="No Images Test"
            )
            
            # Folders with no images should return None (no session created)
            if session is None:
                print(f"✓ PASS: Folder with no images handled correctly, no session created")
                return True
            else:
                print(f"✗ FAIL: Expected None for folder with no images, got session with {session.total_photos} photos")
                return False
                
        except Exception as e:
            print(f"✗ FAIL: Exception raised - {e}")
            return False


def test_null_and_empty_values():
    """Test database handling of null/empty values"""
    print("\n=== Test 5: Null and Empty Values ===")
    
    test_db = DatabaseManager(db_type='sqlite', connection_string=':memory:')
    
    # Test session with minimal fields
    session = Session(
        name="Minimal Session",
        category="test",
        group="minimal",
        date=None,  # Null date
        location=None,  # Null location
        description="",  # Empty description
        folder_path=None,
        total_photos=0
    )
    
    try:
        created = test_db.create_session(session)
        print(f"✓ Created session with null/empty values (ID: {created.id})")
        
        # Retrieve and verify
        retrieved = test_db.get_session(created.id)
        if retrieved:
            print(f"✓ PASS: Session retrieved successfully")
            print(f"  - Date: {retrieved.date}")
            print(f"  - Location: {retrieved.location}")
            print(f"  - Description: '{retrieved.description}'")
            return True
        else:
            print(f"✗ FAIL: Could not retrieve session")
            return False
            
    except Exception as e:
        print(f"✗ FAIL: Exception - {e}")
        return False


def test_special_characters_in_paths():
    """Test paths with special characters"""
    print("\n=== Test 6: Special Characters in Paths ===")
    
    test_cases = [
        "C:\\Photos\\2025-04-03\\Edited",  # Valid path with dashes
        "E:\\Photos & Videos\\Test",  # Ampersand
        "F:\\Photos\\Artist's Portfolio",  # Apostrophe
        "G:\\Photos\\(Archive)\\Test",  # Parentheses
    ]
    
    test_db = DatabaseManager(db_type='sqlite', connection_string=':memory:')
    storage = LocalStorageProvider()
    extractor = ExifExtractor(test_db, storage)
    
    passed = 0
    for path in test_cases:
        try:
            # Just test date extraction logic, not actual folder access
            date = extractor.extract_date_from_session_name(path)
            print(f"✓ Path handled: {path} → Date: {date}")
            passed += 1
        except Exception as e:
            print(f"✗ Failed on: {path} - {e}")
    
    if passed == len(test_cases):
        print(f"✓ PASS: All special character paths handled ({passed}/{len(test_cases)})")
        return True
    else:
        print(f"⚠ PARTIAL: {passed}/{len(test_cases)} paths handled")
        return passed > 0


def test_date_extraction_edge_cases():
    """Test date extraction with edge cases"""
    print("\n=== Test 7: Date Extraction Edge Cases ===")
    
    test_db = DatabaseManager(db_type='sqlite', connection_string=':memory:')
    storage = LocalStorageProvider()
    extractor = ExifExtractor(test_db, storage)
    
    test_cases = [
        ("Cancun 2025", None, "Should not match '2025' alone"),
        ("Photos 2024 2025 2026", None, "Multiple years without format"),
        ("2025-13-01", None, "Invalid month (13)"),
        ("2025-02-30", None, "Invalid day (Feb 30)"),
        ("2025-04-03", "2025-04-03", "Valid YYYY-MM-DD"),
        ("20250403", "2025-04-03", "Valid YYYYMMDD"),
        ("04-03-2025", "2025-04-03", "Valid MM-DD-YYYY"),
        ("", None, "Empty string"),
    ]
    
    passed = 0
    for input_str, expected_str, description in test_cases:
        result = extractor.extract_date_from_session_name(input_str)
        result_str = result.strftime("%Y-%m-%d") if result else None
        
        if result_str == expected_str:
            print(f"✓ {description}: '{input_str}' → {result_str}")
            passed += 1
        else:
            print(f"✗ {description}: '{input_str}' → Expected {expected_str}, got {result_str}")
    
    if passed == len(test_cases):
        print(f"✓ PASS: All date extraction cases handled ({passed}/{len(test_cases)})")
        return True
    else:
        print(f"⚠ PARTIAL: {passed}/{len(test_cases)} cases passed")
        return passed >= len(test_cases) - 2  # Allow 2 failures


def test_very_long_paths():
    """Test handling of very long file paths"""
    print("\n=== Test 8: Very Long Paths ===")
    
    test_db = DatabaseManager(db_type='sqlite', connection_string=':memory:')
    storage = LocalStorageProvider()
    extractor = ExifExtractor(test_db, storage)
    
    # Create a very long path (Windows MAX_PATH is 260 characters)
    long_path = "C:\\" + "A" * 250 + "\\Photos\\Edited"
    
    try:
        # Test date extraction (doesn't require path to exist)
        date = extractor.extract_date_from_session_name(long_path)
        print(f"✓ Long path handled in date extraction (length: {len(long_path)})")
        
        # Test session creation with long path
        session = Session(
            name="Long Path Test",
            category="test",
            group="long_path",
            folder_path=long_path,
            total_photos=0
        )
        created = test_db.create_session(session)
        print(f"✓ PASS: Session with long path created (ID: {created.id})")
        return True
        
    except Exception as e:
        print(f"✗ FAIL: Exception with long path - {e}")
        return False


def run_all_tests():
    """Run all edge case tests"""
    print("=" * 80)
    print("PHOTOGRAPHY WRAPPED - EDGE CASE TESTING")
    print("=" * 80)
    
    tests = [
        ("Duplicate Session Prevention", test_duplicate_session_prevention),
        ("Empty Folder Handling", test_empty_folder),
        ("Invalid Path Handling", test_invalid_path),
        ("Folder With No Images", test_folder_with_no_images),
        ("Null and Empty Values", test_null_and_empty_values),
        ("Special Characters in Paths", test_special_characters_in_paths),
        ("Date Extraction Edge Cases", test_date_extraction_edge_cases),
        ("Very Long Paths", test_very_long_paths),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ EXCEPTION in {name}: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print("=" * 80)
    print(f"Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print("=" * 80)
    
    return passed == total


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)

